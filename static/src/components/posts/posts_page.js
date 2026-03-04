/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class PostsPage extends Component {
    static template = "alpha_echo.PostsPage";
    static props = {};

    /** Expose _t to the OWL template context */
    get _t() { return _t; }

    setup() {
        this.radarService = useService("alpha_echo.radar_service");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            activeTab: "all",
            searchQuery: "",
            isLoading: false,
            selectedPost: null,
        });

        onWillStart(async () => {
            await this.radarService.initialize();
            await this.loadPosts();
        });
    }

    async loadPosts() {
        this.state.isLoading = true;
        try {
            await this.radarService.loadPosts();
        } finally {
            this.state.isLoading = false;
        }
    }

    get posts() {
        return this.radarService.state.posts;
    }

    get radarState() {
        return this.radarService.state;
    }

    get filteredPosts() {
        const q = this.state.searchQuery.toLowerCase().trim();
        const tab = this.state.activeTab;
        return this.posts.filter((p) => {
            const matchTab =
                tab === "all" ||
                (tab === "draft"     && p.state === "draft") ||
                (tab === "published" && p.state === "published") ||
                (tab === "rejected"  && p.state === "rejected");
            const matchSearch = !q || (
                (p.ai_generated_text && p.ai_generated_text.toLowerCase().includes(q)) ||
                (p.original_text     && p.original_text.toLowerCase().includes(q))     ||
                (p.target_id && p.target_id[1] && p.target_id[1].toLowerCase().includes(q))
            );
            return matchTab && matchSearch;
        });
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    /**
     * Returns a translated label for a post state.
     * @param {string} state - 'draft' | 'published' | 'rejected'
     */
    getPostStatusLabel(state) {
        const labels = {
            draft:     _t("Pending Review"),
            published: _t("Published"),
            rejected:  _t("Rejected"),
        };
        return labels[state] || state;
    }

    openPostModal(post) {
        this.state.selectedPost = Object.assign({}, post);
    }

    closeModal() {
        this.state.selectedPost = null;
    }

    async approveAndPublish() {
        if (!this.state.selectedPost) return;
        try {
            await this.orm.call(
                "alpha.echo.post",
                "write",
                [[this.state.selectedPost.id], { ai_generated_text: this.state.selectedPost.ai_generated_text }]
            );
            await this.orm.call(
                "alpha.echo.post",
                "action_publish",
                [[this.state.selectedPost.id]],
                {}
            );
            this.notification.add(_t("Post approved and sent to X for publishing."), { type: "success" });
            this.state.selectedPost = null;
            await this.loadPosts();
        } catch (e) {
            this.notification.add(_t("Failed to publish post. Please check your X connection."), { type: "danger" });
        }
    }

    async rejectPost() {
        if (!this.state.selectedPost) return;
        try {
            await this.orm.call("alpha.echo.post", "action_reject", [[this.state.selectedPost.id]], {});
            this.notification.add(_t("Post rejected and removed from the queue."), { type: "info" });
            this.state.selectedPost = null;
            await this.loadPosts();
        } catch (e) {
            this.notification.add(_t("Failed to reject post."), { type: "danger" });
        }
    }
}

registry.category("actions").add("alpha_echo.posts_client_action", PostsPage);
