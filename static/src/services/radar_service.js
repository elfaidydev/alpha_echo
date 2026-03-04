/** @odoo-module **/

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

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
                custom_ai_instructions: "",
                target_radar_focus: "",
                x_list_id: "",
                x_auth_token: "",
                x_ct0: "",
                twitterUser: null
            },
            get isOnboarded() {
                const conf = this.config;
                return !!(
                    conf.twitterLinked &&
                    (conf.custom_ai_instructions && conf.custom_ai_instructions.length > 0) &&
                    (conf.x_list_id && conf.x_list_id.length > 0) &&
                    (conf.x_auth_token && conf.x_auth_token.length > 0) &&
                    (conf.x_ct0 && conf.x_ct0.length > 0)
                );
            }
        });

        const canStartEngine = () => {
             return state.isOnboarded;
        };

        // Live Data Mode: Empty initial arrays
        const dummyTexts = [];

        function pushLog(tag, message, type = "info") {
            const timeString = new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            state.logs = [
                { id: Math.random(), time: timeString, tag, message, type },
                ...state.logs
            ].slice(0, 10);
        }


        async function toggleTracking() {
            if (!state.isTracking && !state.isOnboarded) {
                notification.add(_t("Cannot start engine! Please complete the 3 setup steps first (X Account, AI Prompt, X List)."), {
                    type: "danger",
                    title: _t("Operation Refused 🔒"),
                    className: "sr-premium-toast"
                });
                return;
            }
            
            const newState = !state.isTracking;
            state.isLoading = true;
            try {
                // Persist the state to the backend
                await rpc("/alpha_echo/config/save", { is_engine_active: newState });
                state.isTracking = newState;
                state.config.is_engine_active = newState;
                
                pushLog(_t("Administrative Action"), state.isTracking ? _t("Comprehensive exploration engine activated.") : _t("Exploration tasks suspended."), "warning");
                notification.add(state.isTracking ? _t("Engine started successfully.") : _t("Engine stopped."), { type: "info" });
            } catch (e) {
                notification.add(_t("Failed to update engine status."), { type: "danger" });
            } finally {
                state.isLoading = false;
            }
        }

        async function loadTargets(domain = []) {
            state.isLoading = true;
            try {
                state.targets = await rpc("/web/dataset/call_kw/alpha.echo.target/search_read", {
                    model: "alpha.echo.target",
                    method: "search_read",
                    args: [domain, ["name", "handle", "is_active", "posts_count"]],
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
                state.posts = await rpc("/web/dataset/call_kw/alpha.echo.post/search_read", {
                    model: "alpha.echo.post",
                    method: "search_read",
                    args: [domain, ["target_id", "original_text", "ai_generated_text", "state", "create_date"]],
                    kwargs: { limit: limit, order: "create_date desc" }
                });
            } finally {
                state.isLoading = false;
            }
        }

        async function saveTarget(id, vals) {
            if (id === 'new') {
                await rpc("/web/dataset/call_kw/alpha.echo.target/create", {
                    model: "alpha.echo.target",
                    method: "create",
                    args: [[vals]],
                    kwargs: {}
                });
            } else {
                await rpc("/web/dataset/call_kw/alpha.echo.target/write", {
                    model: "alpha.echo.target",
                    method: "write",
                    args: [[id], vals],
                    kwargs: {}
                });
            }
            await loadTargets();
        }

        async function deleteTarget(id) {
            await rpc("/web/dataset/call_kw/alpha.echo.target/unlink", {
                model: "alpha.echo.target",
                method: "unlink",
                args: [[id]],
                kwargs: {}
            });
            await loadTargets();
        }

        async function toggleTarget(target) {
            const newState = !target.is_active;
            await rpc("/web/dataset/call_kw/alpha.echo.target/write", {
                model: "alpha.echo.target",
                method: "write",
                args: [[target.id], { is_active: newState }],
                kwargs: {}
            });
            target.is_active = newState;
        }

        async function fetchConfig() {
            state.isLoading = true;
            try {
                const data = await rpc("/alpha_echo/config/get", {});
                if (!data.error) {
                    // Normalize all string/null/false fields to empty strings to kill autofill triggers
                    for (let key in data) {
                        if (data[key] === false || data[key] === null) {
                            data[key] = "";
                        }
                    }
                    Object.assign(state.config, data);
                    state.isTracking = !!data.is_engine_active;
                    
                    // Critical Fix: Automatically verify connection if keys exist to populate profile info
                    if (state.config.isFullyConfigured) {
                        try {
                            const testResult = await rpc("/alpha_echo/config/test_twitter", {});
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
                const data = await rpc("/alpha_echo/config/save", state.config);
                if (data.error) {
                    notification.add(data.error, { type: "danger" });
                } else {
                    notification.add(_t("Settings saved successfully. Testing connection to X account..."), { type: "info" });
                    
                    // Critical: Refetch to ensure local state matches any backend normalization
                    await fetchConfig();
                    
                    // Immediately test the connection if keys are present
                    if (state.config.isFullyConfigured) {
                        const testResult = await rpc("/alpha_echo/config/test_twitter", {});
                        if (testResult.success) {
                            state.config.twitterLinked = true;
                            state.config.twitterUser = testResult;
                            notification.add(_t("Successfully linked with account: @") + testResult.username, { type: "success" });
                        } else {
                            state.config.twitterLinked = false;
                            state.config.twitterUser = null;
                            notification.add(_t("Failed to link with X account: ") + (testResult.error || _t("Verify your keys.")), { type: "danger" });
                        }
                    } else {
                        state.config.twitterLinked = false;
                        state.config.twitterUser = null;
                    }
                }
                return data;
            } catch (error) {
                notification.add(_t("An error occurred while saving settings or testing connection."), { type: "danger" });
            } finally {
                state.isLoading = false;
            }
        }

        async function disconnectX() {
            state.isLoading = true;
            try {
                const data = await rpc("/alpha_echo/config/disconnect_x", {});
                if (data.success) {
                    state.config.twitterLinked = false;
                    state.config.twitterUser = null;
                    state.isTracking = false;
                    notification.add(_t("X account disconnected and engine stopped."), { type: "success" });
                }
                return data;
            } catch (error) {
                notification.add(_t("Failed to disconnect X account."), { type: "danger" });
            } finally {
                state.isLoading = false;
            }
        }


        return {
            state,
            toggleTracking,
            pushLog,
            loadTargets,
            loadPosts,
            saveTarget,
            deleteTarget,
            toggleTarget,
            fetchConfig,
            saveConfig,
            disconnectX,
            canStartEngine
        };
    }
};

registry.category("services").add("alpha_echo.radar_service", radarService);
