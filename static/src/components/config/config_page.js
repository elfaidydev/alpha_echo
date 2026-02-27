/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class ConfigPage extends Component {
    setup() {
        this.radarService = useService("smart_radar.radar_service");
        this.notification = useService("notification");
        
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
    }

    _initializeDefaultConfig() {
        if (!this.config.scraping_interval) this.config.scraping_interval = 60;
        if (!this.config.max_posts_per_day) this.config.max_posts_per_day = 10;
        
        // Ensure default tags if empty
        if (!this.config.target_radar_focus) {
             this.config.target_radar_focus = "Odoo, ERP, Business";
        }
    }

    get config() {
        return this.radarService.state.config;
    }

    get isLoading() {
        return this.radarService.state.isLoading;
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
            this.notification.add("تم حفط الإعدادات بنجاح", { type: "success" });
        } finally {
            this.state.ui.isSaving = false;
        }
    }

    // --- Connectivity Checks ---
    get isTwitterConnected() {
        return !!(this.config.x_api_key && this.config.x_access_token);
    }
    
    get isOdooBlogConnected() {
        return !!this.config.odoo_blog_id;
    }

    disconnectTwitter() {
        if(confirm("هل أنت متأكد من إلغاء ربط حساب تويتر المعرف حالياً؟")) {
            this.onFieldChange("x_api_key", "");
            this.onFieldChange("x_api_secret", "");
            this.onFieldChange("x_access_token", "");
            this.onFieldChange("x_access_token_secret", "");
            this.notification.add("تم إلغاء ربط حساب تويتر", { type: "warning" });
        }
    }

    // --- Slider Logic ---
    onScrapingIntervalInput(ev) {
        let val = parseInt(ev.target.value) || 15;
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
        if (val === undefined) val = 15;
        // Max: 2880, Min: 15. Range: 2865
        let percent = ((val - 15) / 2865) * 100;
        return percent.toFixed(2);
    }

    getMaxPostsPercent() {
        let val = this.config.max_posts_per_day;
        if (val === undefined) val = 1;
        // Max: 100, Min: 1. Range: 99
        let percent = ((val - 1) / 99) * 100;
        return percent.toFixed(2);
    }

    // --- UI Helpers ---
    onFieldChange(fieldName, value) {
        // Handle integer casting for sliders
        if (['scraping_interval', 'max_posts_per_day', 'odoo_blog_id'].includes(fieldName)) {
            value = parseInt(value) || 0;
        }

        this.config[fieldName] = value;
        
        // Real-time Linked Status Update
        if (['x_api_key', 'x_api_secret', 'x_access_token', 'x_access_token_secret'].includes(fieldName)) {
            this.config.twitterLinked = !!(this.config.x_api_key && this.config.x_api_secret && 
                                          this.config.x_access_token && this.config.x_access_token_secret);
        }

        // Force component render to instantly update t-att-value and inline styles during fast dragging
        this.state.ui.renderTrigger++;
        
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        
        // Auto-save debounce
        this.saveTimeout = setTimeout(() => {
            this.radarService.saveConfig();
        }, 1500);
    }
    
    toggleVisibility(field) {
        this.state.ui[field] = !this.state.ui[field];
    }
}

ConfigPage.template = "smart_radar.ConfigPage";

registry.category("actions").add("smart_radar_action_config", ConfigPage);
