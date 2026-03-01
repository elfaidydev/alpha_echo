/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class TargetsPage extends Component {
    setup() {
        this.radarService = useService("alpha_echo.radar_service");
        this.orm = useService("orm"); // Keep orm for custom modal fetches if needed
        
        this.state = useState({
            activeTab: 'all',
            searchQuery: '',
            selectedTarget: null,
            targetRecentPosts: [],
            modalMode: 'view',
            editForm: {},
            service: this.radarService.state,
        });

        onWillStart(async () => {
            await this.radarService.loadTargets();
        });
    }

    get targets() {
        return this.state.service.targets;
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
        let domain = [];
        if (tabName !== 'all') domain = [['category', '=', tabName]];
        await this.radarService.loadTargets(domain);
    }
    
    async openTargetAnalytics(target) {
        this.state.modalMode = 'view';
        this.state.selectedTarget = target;
        this.state.targetRecentPosts = [];
        
        const posts = await this.orm.searchRead(
            "alpha.echo.post",
            [['target_id', '=', target.id]],
            ["original_text", "ai_generated_text", "ai_confidence", "state", "create_date"],
            { limit: 5, order: "create_date desc" }
        );
        
        if (this.state.selectedTarget && this.state.selectedTarget.id === target.id) {
            this.state.targetRecentPosts = posts;
        }
    }
    
    closeTargetAnalytics() {
        this.state.selectedTarget = null;
        this.state.targetRecentPosts = [];
        this.state.modalMode = 'view';
        this.state.editForm = {};
    }
    
    openCreateModal() {
        this.state.modalMode = 'create';
        this.state.editForm = { name: '', handle: '', category: 'general', is_active: true };
        this.state.selectedTarget = { id: 'new', name: _t('Add New Source') };
    }

    editTarget() {
        this.state.modalMode = 'edit';
        this.state.editForm = {
            name: this.state.selectedTarget.name,
            handle: this.state.selectedTarget.handle,
            category: this.state.selectedTarget.category,
            is_active: this.state.selectedTarget.is_active,
        };
    }

    handleInputChange(ev, field) {
        this.state.editForm[field] = field === 'is_active' ? ev.target.checked : ev.target.value;
    }

    async saveTarget() {
        if (!this.state.editForm.name) return;
        await this.radarService.saveTarget(this.state.selectedTarget.id, this.state.editForm);
        this.closeTargetAnalytics();
    }

    async deleteTarget() {
        if (confirm(_t("Are you sure you want to delete this source? This action cannot be undone."))) {
            await this.radarService.deleteTarget(this.state.selectedTarget.id);
            this.closeTargetAnalytics();
        }
    }
    
    async toggleTracking(target) {
        await this.radarService.toggleTarget(target);
    }
}

TargetsPage.template = "alpha_echo.TargetsPage";
registry.category("actions").add("alpha_echo.targets_client_action", TargetsPage);
