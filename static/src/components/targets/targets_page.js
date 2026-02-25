/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class TargetsPage extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            targets: [],
            activeTab: 'all', // 'all', 'general', 'health', 'education', 'tech'
            searchQuery: '', // Real-time search
            isLoading: true,
            selectedTarget: null, // For the new Premium Modal
            targetRecentPosts: [], // Fetched asynchronously for blazing speed
            modalMode: 'view', // 'view', 'edit', 'create'
            editForm: {}, // Stores data during creation/editing
        });

        onWillStart(async () => {
            await this.loadTargets();
        });
    }

    get filteredTargets() {
        if (!this.state.searchQuery) return this.state.targets;
        const q = this.state.searchQuery.toLowerCase();
        return this.state.targets.filter(t => 
            (t.name && t.name.toLowerCase().includes(q)) ||
            (t.handle && t.handle.toLowerCase().includes(q))
        );
    }

    async loadTargets() {
        this.state.isLoading = true;
        let domain = [];
        if (this.state.activeTab !== 'all') {
            domain = [['category', '=', this.state.activeTab]];
        }
        
        this.state.targets = await this.orm.searchRead(
            "smart.radar.target",
            domain,
            ["name", "handle", "category", "is_active", "posts_count"],
            { order: "name asc" }
        );
        this.state.isLoading = false;
    }

    async setTab(tabName) {
        this.state.activeTab = tabName;
        await this.loadTargets();
    }
    
    // Blazing fast Premium Modal Launch (View Mode)
    async openTargetAnalytics(target) {
        this.state.modalMode = 'view';
        this.state.selectedTarget = target;
        this.state.targetRecentPosts = []; // Show loading state for posts timeline
        
        // Asynchronously fetch the latest 5 posts for this specific target
        const posts = await this.orm.searchRead(
            "smart.radar.post",
            [['target_id', '=', target.id]],
            ["original_text", "ai_generated_text", "ai_confidence", "state", "create_date"],
            { limit: 5, order: "create_date desc" }
        );
        
        // Only update if the modal is still open for the same target
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
    
    // --- Premium Custom CRUD (Zero-Reload) ---
    
    openCreateModal() {
        this.state.modalMode = 'create';
        this.state.editForm = { name: '', handle: '', category: 'general', is_active: true };
        this.state.selectedTarget = { id: 'new', name: 'إضافة جهة جديدة' }; // Virtual target to open modal
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
        if (field === 'is_active') {
            this.state.editForm[field] = ev.target.checked;
        } else {
            this.state.editForm[field] = ev.target.value;
        }
    }

    async saveTarget() {
        if (!this.state.editForm.name) return; // Simple validation
        
        const vals = {
            name: this.state.editForm.name,
            handle: this.state.editForm.handle,
            category: this.state.editForm.category,
            is_active: this.state.editForm.is_active,
        };

        if (this.state.modalMode === 'create') {
            await this.orm.create("smart.radar.target", [vals]);
        } else if (this.state.modalMode === 'edit') {
            await this.orm.write("smart.radar.target", [this.state.selectedTarget.id], vals);
        }
        
        this.closeTargetAnalytics();
        await this.loadTargets(); // Refresh the grid instantly
    }
    
    // Toggle Tracking
    async toggleTracking(target) {
        const newState = !target.is_active;
        await this.orm.write("smart.radar.target", [target.id], {
            is_active: newState
        });
        target.is_active = newState; // Update local state immediately for snappy UI
    }
}

TargetsPage.template = "smart_radar.TargetsPage";
registry.category("actions").add("smart_radar.targets_client_action", TargetsPage);
