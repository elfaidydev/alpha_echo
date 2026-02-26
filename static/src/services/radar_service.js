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
            isTracking: true,
            isLoading: false,
            monitoredAccounts: 350,
            grantsDiscovered: 7,
            publishedToday: 14,
            matchRate: 98,
            feed: [],
            logs: [],
            targets: [],
            posts: [],
            activeTab: 'all',
            searchQuery: '',
            config: {}
        });

        // NGO/Donor Mock Data
        const dummyTexts = [
            { 
                donor: "@Alwaleed_Philan",
                raw: "تعلن مؤسسة الوليد للإنسانية عن فتح باب التقديم للحصول على تمويل مشاريع الإسكان وتنمية المجتمع لعام ٢٠٢٤ عبر البوابة الإلكترونية. آخر موعد للتقديم نهاية الشهر.", 
                ai: "إعلان استراتيجي: نُعلم شركاءنا بفتح نافذة التمويل لمشاريع الإسكان وتنمية المجتمع التابعة لمؤسسة الوليد للإنسانية (دورة 2024). يُرجى الاطلاع على المحددات والمعايير لضمان استيفاء الشروط وتوثيق الملفات قبل الموعد. [المرجع الرسمي]" 
            },
            { 
                donor: "@USAIDMiddleEast",
                raw: "USAID announces $5 million in new grant funding for climate resilience initiatives in the MENA region. Seeking local partners and NGOs.", 
                ai: "مبادرة دولية: أطلقت الوكالة الأمريكية للتنمية الدولية محفظة دعم بقيمة 5 ملايين دولار مخصصة لبرامج الاستدامة والمناخ في الشرق الأوسط. ندعو كافة الجهات المعنية لمراجعة الآليات وبناء الشراكات. [الوثيقة الرسمية]" 
            },
            { 
                donor: "@KSRelief",
                raw: "يطلق مركز الملك سلمان للإغاثة والأعمال الإنسانية برنامج تمويل الشراكات لدعم المنظمات الصحية والتعليمية في الدول النامية. للمشاركة تفضل بالتسجيل.", 
                ai: "فرصة شراكة إنسانية: أقر مركز الملك سلمان للإغاثة برنامجه الجديد لتمويل الشراكات الفاعلة في قطاعي الصحة والتعليم. تتوفر لدينا الآن إرشادات التسجيل ونماذج حوكمة التمويل للجهات المهتمة بالشراكة التشغيلية. [دليل البرنامج]" 
            },
            { 
                donor: "@isdb_stories",
                raw: "يسر البنك الإسلامي للتنمية دعوة المبتكرين للتقديم على صندوق دعم الاستدامة والابتكار لعام ٢٠٢٤.", 
                ai: "دعوة تقديم: يعلن البنك الإسلامي للتنمية عن إطلاق صندوق المستجدات التمويلية لدعم الابتكار. نوفر لعملائنا تحليلاً دقيقاً لمتطلبات الصندوق لضمان التنافسية ورفع موثوقية العروض التقنية والمجتمعية. [رابط الاستعلام]" 
            }
        ];

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
                // In production, this would be an RPC call to Odoo or a Supabase Fetch
                // await rpc("/smart_radar/fetch_feed", {});
                
                // For now, mock a delay
                await new Promise(r => setTimeout(r, 800));
                
                const template = dummyTexts[Math.floor(Math.random() * dummyTexts.length)];
                const timeString = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });

                const newItem = {
                    id: Math.random(),
                    time: timeString,
                    donor: template.donor,
                    original: template.raw,
                    rewritten: template.ai,
                    tweetLink: "https://twitter.com/odoo"
                };

                state.feed = [newItem, ...state.feed].slice(0, 8);
                
                pushLog("تحديث تشغيلي", `رصد نشاط بيانات صادرة عن معرّف ${template.donor}.`, "info");
                setTimeout(() => pushLog("تدخل المعالج (AI)", `يجري تطبيق معايير الصياغة المؤسسية والتهيئة للنشر...`, "primary"), 800);
                setTimeout(() => {
                    pushLog("المزامنة الآلية", `تمت المصادقة وتصدير المحتوى بنجاح عبر البوابات الرسمية.`, "success");
                    state.grantsDiscovered += 1;
                    state.publishedToday += 2;
                }, 1800);

            } finally {
                state.isLoading = false;
            }
        }

        function toggleTracking() {
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
                    // Use Object.assign to keep the reactive reference intact
                    Object.assign(state.config, data);
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
                    notification.add("تم تحديث بروتوكولات النظام بنجاح.", { type: "success" });
                }
                return data;
            } catch (error) {
                notification.add("حدث خطأ أثناء محاولة حفظ الإعدادات.", { type: "danger" });
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
            saveConfig
        };
    }
};

registry.category("services").add("smart_radar.radar_service", radarService);
