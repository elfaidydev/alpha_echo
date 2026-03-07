/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class TargetsPage extends Component {
    static template = "alpha_echo.TargetsPage";
    static props = {};

    /** Expose _t to the OWL template context */
    get _t() { return _t; }

    setup() {
        this.radarService = useService("alpha_echo.radar_service");
        this.notification  = useService("notification");
        this.orm           = useService("orm");

        this.state = useState({
            searchQuery: "",
            activeTab: "all", // 'all', 'active', 'inactive'
            isModalOpen: false,
            modalMode: "edit", // 'add' or 'edit'
            targetRecentPosts: [],
            // Field states for the modal
            editingTarget: {
                id: null,
                name: "",
                handle: "",
                is_active: true,
                posts_count: 0
            },
            isSaving: false
        });

        onWillStart(async () => {
            await this.radarService.initialize();
            await this.radarService.loadTargets();
        });
    }

    get radarState() {
        return this.radarService.state;
    }

    get filteredTargets() {
        const q = this.state.searchQuery.toLowerCase().trim();
        let targets = this.radarState.targets;

        // Apply Tab Filter
        if (this.state.activeTab === 'active') {
            targets = targets.filter(t => t.is_active);
        } else if (this.state.activeTab === 'inactive') {
            targets = targets.filter(t => !t.is_active);
        }

        if (!q) return targets;
        return targets.filter(
            (t) =>
                (t.name   && t.name.toLowerCase().includes(q)) ||
                (t.handle && t.handle.toLowerCase().includes(q))
        );
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    async addTarget() {
        this.state.modalMode = "add";
        this.state.editingTarget = { id: null, name: "", handle: "", is_active: true, posts_count: 0 };
        this.state.targetRecentPosts = [];
        this.state.isModalOpen = true;
    }

    async openTargetDetails(target) {
        this.state.modalMode = "edit";
        this.state.editingTarget = { ...target };
        this.state.targetRecentPosts = [];
        this.state.isModalOpen = true;
        
        try {
            const posts = await this.orm.searchRead(
                "alpha.echo.post",
                [["target_id", "=", target.id]],
                ["ai_generated_text", "original_text", "state", "create_date"],
                { limit: 5, order: "create_date desc" }
            );
            this.state.targetRecentPosts = posts;
        } catch (e) {
            console.error("Failed to load posts", e);
        }
    }

    closeModal() {
        this.state.isModalOpen = false;
        this.state.isSaving = false;
    }

    async saveTarget() {
        const t = this.state.editingTarget;
        if (!t.name || !t.handle) {
            this.notification.add(_t("Please provide both Name and X Handle."), { type: "warning" });
            return;
        }

        this.state.isSaving = true;
        try {
            if (this.state.modalMode === "add") {
                await this.radarService.saveTarget('new', { name: t.name, handle: t.handle, is_active: t.is_active });
                this.notification.add(_t("Target added successfully."), { type: "success" });
            } else {
                await this.radarService.saveTarget(t.id, { name: t.name, handle: t.handle, is_active: t.is_active });
                this.notification.add(_t("Target updated successfully."), { type: "success" });
            }
            this.closeModal();
        } catch (e) {
            this.notification.add(_t("Failed to save target."), { type: "danger" });
        } finally {
            this.state.isSaving = false;
        }
    }

    async deleteTarget() {
        const id = this.state.editingTarget.id;
        if (!id) return;
        
        if (!confirm(_t("Are you sure you want to delete this target?"))) return;

        try {
            await this.radarService.deleteTarget(id);
            this.notification.add(_t("Target removed."), { type: "success" });
            this.closeModal();
        } catch (e) {
            this.notification.add(_t("Failed to remove target."), { type: "danger" });
        }
    }

    async refreshTargets() {
        await this.radarService.loadTargets();
        this.notification.add(_t("Sync complete."), { type: "info" });
    }

    getEngineStatusLabel(isActive) {
        return isActive ? _t("Active") : _t("Inactive");
    }

    getPostStatusLabel(state) {
        const labels = { draft: _t("In Review"), published: _t("Published"), rejected: _t("Rejected") };
        return labels[state] || state;
    }
}

registry.category("actions").add("alpha_echo.targets_client_action", TargetsPage);
