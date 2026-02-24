/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class PostsPage extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            posts: [],
            activeTab: 'draft', // 'all', 'draft', 'published'
            selectedPost: null, // For modal
            searchQuery: '', // Real-time search
        });

        onWillStart(async () => {
            await this.loadPosts();
        });
    }

    get filteredPosts() {
        if (!this.state.searchQuery) return this.state.posts;
        const q = this.state.searchQuery.toLowerCase();
        return this.state.posts.filter(p => 
            (p.target_id[1] && p.target_id[1].toLowerCase().includes(q)) ||
            (p.ai_generated_text && p.ai_generated_text.toLowerCase().includes(q)) ||
            (p.original_text && p.original_text.toLowerCase().includes(q))
        );
    }

    async loadPosts() {
        let domain = [];
        if (this.state.activeTab !== 'all') {
            domain = [['state', '=', this.state.activeTab]];
        }
        
        this.state.posts = await this.orm.searchRead(
            "smart.radar.post",
            domain,
            ["target_id", "source_url", "original_text", "ai_generated_text", "ai_confidence", "state", "create_date"],
            { order: "create_date desc" }
        );
    }

    async setTab(tabName) {
        this.state.activeTab = tabName;
        await this.loadPosts();
    }

    openPostModal(post) {
        this.state.selectedPost = post;
    }

    closeModal() {
        this.state.selectedPost = null;
    }

    async approveAndPublish() {
        if (!this.state.selectedPost) return;
        
        // Save the edited text first just in case
        await this.orm.write("smart.radar.post", [this.state.selectedPost.id], {
            ai_generated_text: this.state.selectedPost.ai_generated_text
        });

        // Publish
        await this.orm.call("smart.radar.post", "action_publish", [[this.state.selectedPost.id]]);
        
        this.closeModal();
        await this.loadPosts(); // Refresh list
    }

    async rejectPost() {
        if (!this.state.selectedPost) return;
        
        // Reject
        await this.orm.call("smart.radar.post", "action_reject", [[this.state.selectedPost.id]]);
        
        this.closeModal();
        await this.loadPosts(); // Refresh list
    }
}

PostsPage.template = "smart_radar.PostsPage";
registry.category("actions").add("smart_radar.posts_client_action", PostsPage);
