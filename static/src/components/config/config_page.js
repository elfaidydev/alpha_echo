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
                showTenantId: false,
                showTwitterApiKey: false,
                showTwitterApiSecret: false,
                showTwitterAccessToken: false,
                showTwitterAccessSecret: false,
                newKeyword: "",
            }
        });

        onWillStart(async () => {
            await this.radarService.fetchConfig();
        });
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
        } finally {
            this.state.ui.isSaving = false;
        }
    }

    // --- UI Helpers ---
    onFieldChange(fieldName, value) {
        this.config[fieldName] = value;
        
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        
        this.saveTimeout = setTimeout(() => {
            this.radarService.saveConfig();
        }, 1200);
    }
    
    toggleVisibility(field) {
        this.state.ui[field] = !this.state.ui[field];
    }
}

ConfigPage.template = "smart_radar.ConfigPage";

registry.category("actions").add("smart_radar_action_config", ConfigPage);
