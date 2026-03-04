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
            selectedTarget: null,
            targetRecentPosts: [],
        });

        onWillStart(async () => {
            await this.radarService.loadTargets();
        });
    }

    get radarState() {
        return this.radarService.state;
    }

    get filteredTargets() {
        const q = this.state.searchQuery.toLowerCase().trim();
        const targets = this.radarState.targets;
        if (!q) return targets;
        return targets.filter(
            (t) =>
                (t.name   && t.name.toLowerCase().includes(q)) ||
                (t.handle && t.handle.toLowerCase().includes(q))
        );
    }

    /**
     * Returns a translated label for a boolean active flag.
     * @param {boolean} isActive
     */
    getEngineStatusLabel(isActive) {
        return isActive ? _t("Active") : _t("Inactive");
    }

    /**
     * Returns a translated label for the selected target's active status.
     */
    getSelectedTargetStatusLabel() {
        if (!this.state.selectedTarget) return "";
        return this.state.selectedTarget.is_active ? _t("Active &amp; Capturing") : _t("Monitoring Paused");
    }

    /**
     * Returns a translated post state label for the analytics timeline.
     * @param {string} state
     */
    getPostStatusLabel(state) {
        const labels = {
            draft:     _t("In Review"),
            published: _t("Published"),
            rejected:  _t("Rejected"),
        };
        return labels[state] || state;
    }

    async openTargetAnalytics(target) {
        this.state.selectedTarget = target;
        this.state.targetRecentPosts = [];
        try {
            const posts = await this.orm.searchRead(
                "alpha.echo.post",
                [["target_id", "=", target.id]],
                ["ai_generated_text", "original_text", "state", "create_date"],
                { limit: 5, order: "create_date desc" }
            );
            this.state.targetRecentPosts = posts;
        } catch (e) {
            this.notification.add(_t("Failed to load recent posts for this target."), { type: "warning" });
        }
    }

    closeTargetAnalytics() {
        this.state.selectedTarget = null;
        this.state.targetRecentPosts = [];
    }

    async deleteTarget(id) {
        try {
            await this.radarService.deleteTarget(id);
            this.notification.add(_t("Target removed successfully."), { type: "success" });
        } catch (e) {
            this.notification.add(_t("Failed to remove target."), { type: "danger" });
        }
    }
}

registry.category("actions").add("alpha_echo.targets_client_action", TargetsPage);
