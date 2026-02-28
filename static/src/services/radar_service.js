/** @odoo-module **/

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";

/**
 * RadarService - The "Core" JS Layer
 * Handles data orchestration, business logic, and cross-component state.
 * Decouples the UI from the data source (Odoo RPC/Supabase).
 */
export const radarService = {
    dependencies: ["rpc", "notification"],
    
    start(env, { rpc, notification }) {
        const state = reactive({
            isTracking: false, // Default to OFF for new clients
            isLoading: false,
            monitoredAccounts: 0, // Starts at 0
            grantsDiscovered: 0,
            publishedToday: 0,
            matchRate: 0,
            feed: [],
            logs: [],
            targets: [],
            posts: [],
            activeTab: 'all',
            searchQuery: '',
            config: {
                scraping_interval: 180,
                max_posts_per_day: 100,
                x_api_key: "",
                x_api_secret: "",
                x_access_token: "",
                x_access_token_secret: "",
                openai_api_key: "",
                apify_token: "",
                apify_actor_id: "",
                supabase_url: "",
                supabase_key: "",
                twitterLinked: false,
                get isFullyConfigured() {
                    return !!(this.x_api_key && this.x_api_secret && this.x_access_token && this.x_access_token_secret);
                },
                systemPrompt: false,
                target_radar_focus: "",
                twitterUser: null
            }
        });

        const canStartEngine = () => {
             // System can only "start" if linked AND targets exist
             return state.config.twitterLinked && state.targets.length > 0;
        };

        // Live Data Mode: Empty initial arrays
        const dummyTexts = [];

        function pushLog(tag, message, type = "info") {
            const timeString = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            state.logs = [
                { id: Math.random(), time: timeString, tag, message, type },
                ...state.logs
            ].slice(0, 10);
        }

        async function fetchFeed() {
            state.isLoading = true;
            try {
                notification.add("بدأت عملية البحث والاستكشاف (Apify)...", { type: "info" });
                
                // Call the real backend coordination logic
                await rpc("/web/dataset/call_kw/smart.radar.target/cron_fetch_all_targets", {
                    model: "smart.radar.target",
                    method: "cron_fetch_all_targets",
                    args: [],
                    kwargs: {}
                });
                
                // Reload data to reflect changes
                await loadPosts();
                await loadTargets();
                
                notification.add("اكتملت مراجعة المصادر وصياغة المحتوى الجديد بنجاح.", { type: "success" });
                pushLog("تزامن يدوي", "تم الانتهاء من فحص كافة المصادر النشطة وجلب التحديثات.", "success");

            } catch (error) {
                notification.add("فشلت عملية الجلب التلقائي. تأكد من إعدادات الربط والإنترنت.", { type: "danger" });
                pushLog("خطأ في المزامنة", error.message || "فشل الاتصال بـ Apify أو OpenAI.", "danger");
            } finally {
                state.isLoading = false;
            }
        }

        function toggleTracking() {
            if (!state.isTracking && !canStartEngine()) {
                notification.add("لا يمكن تشغيل المحرك! تعذر العثور على مفاتيح المعالجة (APIs) أو لم يتم إدراج مصادر رصد (Targets) في النظام.", {
                    type: "danger",
                    title: "عملية مرفوضة 🔒",
                    className: "sr-premium-toast"
                });
                return;
            }
            state.isTracking = !state.isTracking;
            pushLog("إجراء إداري", state.isTracking ? "تم تفعيل محرك الاستكشاف الشامل." : "تعليق المهام الاستكشافية.", "warning");
        }

        async function loadTargets(domain = []) {
            state.isLoading = true;
            try {
                state.targets = await rpc("/web/dataset/call_kw/smart.radar.target/search_read", {
                    model: "smart.radar.target",
                    method: "search_read",
                    args: [domain, ["name", "handle", "category", "is_active", "posts_count"]],
                    kwargs: { order: "name asc" }
                });
                state.monitoredAccounts = state.targets.length;
            } finally {
                state.isLoading = false;
            }
        }

        async function loadPosts(domain = [], limit = 40) {
            state.isLoading = true;
            try {
                state.posts = await rpc("/web/dataset/call_kw/smart.radar.post/search_read", {
                    model: "smart.radar.post",
                    method: "search_read",
                    args: [domain, ["target_id", "original_text", "ai_generated_text", "ai_confidence", "state", "create_date"]],
                    kwargs: { limit: limit, order: "create_date desc" }
                });
            } finally {
                state.isLoading = false;
            }
        }

        async function saveTarget(id, vals) {
            if (id === 'new') {
                await rpc("/web/dataset/call_kw/smart.radar.target/create", {
                    model: "smart.radar.target",
                    method: "create",
                    args: [[vals]],
                    kwargs: {}
                });
            } else {
                await rpc("/web/dataset/call_kw/smart.radar.target/write", {
                    model: "smart.radar.target",
                    method: "write",
                    args: [[id], vals],
                    kwargs: {}
                });
            }
            await loadTargets();
        }

        async function toggleTarget(target) {
            const newState = !target.is_active;
            await rpc("/web/dataset/call_kw/smart.radar.target/write", {
                model: "smart.radar.target",
                method: "write",
                args: [[target.id], { is_active: newState }],
                kwargs: {}
            });
            target.is_active = newState;
        }

        async function fetchConfig() {
            state.isLoading = true;
            try {
                const data = await rpc("/smart_radar/config/get", {});
                if (!data.error) {
                    Object.assign(state.config, data);
                    
                    // Critical Fix: Automatically verify connection if keys exist to populate profile info
                    if (state.config.isFullyConfigured) {
                        try {
                            const testResult = await rpc("/smart_radar/config/test_twitter", {});
                            if (testResult && testResult.success) {
                                state.config.twitterLinked = true;
                                state.config.twitterUser = testResult;
                            } else {
                                state.config.twitterLinked = false;
                                state.config.twitterUser = null;
                            }
                        } catch (e) {
                            state.config.twitterLinked = false;
                            state.config.twitterUser = null;
                        }
                    } else {
                        state.config.twitterLinked = false;
                        state.config.twitterUser = null;
                    }
                }
                return data;
            } finally {
                state.isLoading = false;
            }
        }

        async function saveConfig() {
            state.isLoading = true;
            try {
                const data = await rpc("/smart_radar/config/save", state.config);
                if (data.error) {
                    notification.add(data.error, { type: "danger" });
                } else {
                    notification.add("تم حفظ الإعدادات بنجاح. جاري اختبار الاتصال بحساب X...", { type: "info" });
                    
                    // Immediately test the connection if keys are present
                    if (state.config.isFullyConfigured) {
                        const testResult = await rpc("/smart_radar/config/test_twitter", {});
                        if (testResult.success) {
                            state.config.twitterLinked = true;
                            state.config.twitterUser = testResult;
                            notification.add(`تم الربط بنجاح مع حساب: @${testResult.username}`, { type: "success" });
                        } else {
                            state.config.twitterLinked = false;
                            state.config.twitterUser = null;
                            notification.add(`فشل الربط بحساب X: ${testResult.error || 'تأكد من صحة المفاتيح.'}`, { type: "danger" });
                        }
                    } else {
                        state.config.twitterLinked = false;
                        state.config.twitterUser = null;
                    }
                }
                return data;
            } catch (error) {
                notification.add("حدث خطأ أثناء محاولة حفظ الإعدادات أو اختبار الاتصال.", { type: "danger" });
            } finally {
                state.isLoading = false;
            }
        }

        return {
            state,
            fetchFeed,
            toggleTracking,
            pushLog,
            loadTargets,
            loadPosts,
            saveTarget,
            toggleTarget,
            fetchConfig,
            saveConfig,
            canStartEngine
        };
    }
};

registry.category("services").add("smart_radar.radar_service", radarService);
