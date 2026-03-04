/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class TargetsPage extends Component {
    setup() {
        this.radarService = useService("alpha_echo.radar_service");
        this.orm = useService("orm");
        this.actionService = useService("action");
        
        this._t = _t;
        this.radarState = useState(this.radarService.state);
        this.state = useState({
            activeTab: 'all',
            searchQuery: '',
            selectedTarget: null,
            targetRecentPosts: [],
        });

        onWillStart(async () => {
            await this.radarService.loadTargets();
        });
    }

    async syncListMembers() {
        await this.radarService.syncListMembers();
    }
    async deleteTarget(id) {
        if (confirm(_t("Are you sure you want to delete this target?"))) {
            await this.radarService.deleteTarget(id);
        }
    }

    get targets() {
        return this.radarState.targets;
    }

    get filteredTargets() {
        if (!this.state.searchQuery) return this.targets;
        const q = this.state.searchQuery.toLowerCase();
        return this.targets.filter(t => 
            (t.name && t.name.toLowerCase().includes(q)) ||
            (t.handle && t.handle.toLowerCase().includes(q))
        );
    }

    async setTab(tabName) {
        this.state.activeTab = tabName;
        // Always load all targets since categories are removed
        await this.radarService.loadTargets();
    }
    
    async openTargetAnalytics(target) {
        this.state.selectedTarget = target;
        this.state.targetRecentPosts = [];
        
        const posts = await this.orm.searchRead(
            "alpha.echo.post",
            [['target_id', '=', target.id]],
            ["original_text", "ai_generated_text", "state", "create_date"],
            { limit: 5, order: "create_date desc" }
        );
        
        if (this.state.selectedTarget && this.state.selectedTarget.id === target.id) {
            this.state.targetRecentPosts = posts;
        }
    }
    
    closeTargetAnalytics() {
        this.state.selectedTarget = null;
        this.state.targetRecentPosts = [];
    }

    // (Removed category mappings)


    getEngineStatusLabel(isActive) {
        return isActive ? _t('Exploration engine active') : _t('Monitoring system paused');
    }

    getSelectedTargetStatusLabel() {
        return this.state.selectedTarget.is_active ? _t('Active \u0026 Capturing') : _t('Paused');
    }

    // (Removed getSelectedTargetCategoryLabel)

    getPostStatusLabel(state) {
        const states = {
            'published': _t('Published'),
            'draft': _t('Pending Draft'),
            'rejected': _t('Rejected')
        };
        return states[state] || _t('Rejected');
    }
}

TargetsPage.template = "alpha_echo.TargetsPage";
registry.category("actions").add("alpha_echo.targets_client_action", TargetsPage);
