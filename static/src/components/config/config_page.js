/** @odoo-module **/

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { localization } from "@web/core/l10n/localization";

export class ConfigPage extends Component {
    get isRTL() { return localization.direction === "rtl"; }

    setup() {
        this.radarService = useService("alpha_echo.radar_service");
        this.notification = useService("notification");
        
        // Track the entire service state for reactive UI updates
        this.serviceState = useState(this.radarService.state);
        
        this.state = useState({
            ui: {
                isSaving: false,
                showTwitterApiKey: false,
                showTwitterApiSecret: false,
                showTwitterAccessToken: false,
                showTwitterAccessSecret: false,
                newKeyword: "",
                renderTrigger: 0,
            }
        });

        onWillStart(async () => {
            await this.radarService.fetchConfig();
            this._initializeDefaultConfig();
        });

        onWillUnmount(async () => {
            if (this.saveTimeout) {
                clearTimeout(this.saveTimeout);
                await this.radarService.saveConfig();
            }
        });
    }

    _initializeDefaultConfig() {
        if (this.config.scraping_interval === undefined) this.config.scraping_interval = 180;
        if (this.config.max_posts_per_day === undefined) this.config.max_posts_per_day = 0;
        
        // Ensure default tags if empty
        if (!this.config.target_radar_focus) {
             this.config.target_radar_focus = "";
        }
    }

    get config() {
        return this.serviceState.config;
    }

    get isLoading() {
        return this.serviceState.isLoading;
    }

    // --- Keyword Tag Logic ---
    get keywords() {
        const focus = this.config.target_radar_focus || "";
        return focus.split(",").map(k => k.trim()).filter(k => k !== "");
    }

    addKeyword(ev) {
        if (ev.key === "Enter" || ev.key === ",") {
            ev.preventDefault();
            const val = this.state.ui.newKeyword.trim();
            if (val && !this.keywords.includes(val)) {
                const current = this.keywords;
                current.push(val);
                this.onFieldChange("target_radar_focus", current.join(","));
                this.state.ui.newKeyword = "";
            }
        }
    }

    removeKeyword(keyword) {
        const filtered = this.keywords.filter(k => k !== keyword);
        this.onFieldChange("target_radar_focus", filtered.join(","));
    }

    async saveConfig() {
        this.state.ui.isSaving = true;
        try {
            await this.radarService.saveConfig();
            this.notification.add(_t("Settings saved successfully"), { type: "success" });
        } finally {
            this.state.ui.isSaving = false;
        }
    }

    // --- Connectivity Checks ---
    get isTwitterConnected() {
        // Only consider it connected if the backend successfully verified the account
        return !!(this.config.twitterLinked && this.config.twitterUser);
    }
    
    get isOdooBlogConnected() {
        return !!this.config.odoo_blog_id;
    }

    async disconnectTwitter() {
        if(confirm(_t("Are you sure you want to unlink the currently identified Twitter account? This will stop automated publishing."))) {
            this.config.x_api_key = "";
            this.config.x_api_secret = "";
            this.config.x_access_token = "";
            this.config.x_access_token_secret = "";
            this.config.twitterLinked = false;
            this.config.twitterUser = null;
            
            // Persist the disconnection
            await this.radarService.saveConfig();
            this.notification.add(_t("Account unlinked successfully."), { type: "info" });
        }
    }

    // --- Slider Logic ---
    onScrapingIntervalInput(ev) {
        let val = parseInt(ev.target.value) || 60;
        this.config.scraping_interval = val;
        this.state.ui.renderTrigger++;
        
        if (this.saveTimeout) clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => this.radarService.saveConfig(), 1500);
    }

    onMaxPostsInput(ev) {
        let val = parseInt(ev.target.value) || 1;
        this.config.max_posts_per_day = val;
        this.state.ui.renderTrigger++;
        
        if (this.saveTimeout) clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => this.radarService.saveConfig(), 1500);
    }

    getScrapingIntervalPercent() {
        let val = this.config.scraping_interval;
        if (val === undefined) val = 60;
        // Max: 2880, Min: 5. Range: 2875
        let percent = ((val - 5) / 2875) * 100;
        return percent.toFixed(2);
    }

    getMaxPostsPercent() {
        let val = this.config.max_posts_per_day;
        if (val === undefined) val = 0;
        return Math.min(100, Math.max(0, val)).toFixed(0);
    }

    // --- UI Helpers ---
    onFieldChange(fieldName, value) {
        // Handle integer casting for sliders
        if (['scraping_interval', 'max_posts_per_day', 'odoo_blog_id'].includes(fieldName)) {
            value = parseInt(value) || 0;
        }

        this.config[fieldName] = value;
        
        // Update linked status logic removed from here as it should be handled by the service test_twitter result
        // to avoid UI flicker while typing.

        // Force component render to instantly update t-att-value and inline styles during fast dragging
        this.state.ui.renderTrigger++;
        
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }

        // Auto-save debounce (Skip for Twitter keys to allow manual linking via button)
        const isTwitterField = ['x_api_key', 'x_api_secret', 'x_access_token', 'x_access_token_secret'].includes(fieldName);
        
        if (!isTwitterField) {
            this.saveTimeout = setTimeout(() => {
                this.radarService.saveConfig();
            }, 2000);
        }
    }
    
    toggleVisibility(field) {
        this.state.ui[field] = !this.state.ui[field];
    }
}

ConfigPage.template = "alpha_echo.ConfigPage";

registry.category("actions").add("alpha_echo_action_config", ConfigPage);
