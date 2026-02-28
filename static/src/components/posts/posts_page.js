/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class PostsPage extends Component {
    setup() {
        this.radarService = useService("alpha_echo.radar_service");
        this.orm = useService("orm"); // Keep orm for custom actions
        
        this.state = useState({
            activeTab: 'all', // 'all', 'draft', 'published'
            selectedPost: null, // For modal
            searchQuery: '', // Real-time search
            service: this.radarService.state,
        });

        onWillStart(async () => {
            await this.radarService.loadPosts();
        });
    }

    get posts() {
        return this.state.service.posts;
    }

    get filteredPosts() {
        if (!this.state.searchQuery) return this.posts;
        const q = this.state.searchQuery.toLowerCase();
        return this.posts.filter(p => 
            (p.target_id[1] && p.target_id[1].toLowerCase().includes(q)) ||
            (p.ai_generated_text && p.ai_generated_text.toLowerCase().includes(q)) ||
            (p.original_text && p.original_text.toLowerCase().includes(q))
        );
    }

    async setTab(tabName) {
        this.state.activeTab = tabName;
        let domain = [];
        if (tabName !== 'all') domain = [['state', '=', tabName]];
        await this.radarService.loadPosts(domain);
    }

    openPostModal(post) {
        this.state.selectedPost = post;
    }

    closeModal() {
        this.state.selectedPost = null;
    }

    async approveAndPublish() {
        if (!this.state.selectedPost) return;
        
        await this.orm.write("alpha.echo.post", [this.state.selectedPost.id], {
            ai_generated_text: this.state.selectedPost.ai_generated_text
        });

        await this.orm.call("alpha.echo.post", "action_publish", [[this.state.selectedPost.id]]);
        
        this.closeModal();
        await this.radarService.loadPosts(); 
    }

    async rejectPost() {
        if (!this.state.selectedPost) return;
        
        await this.orm.call("alpha.echo.post", "action_reject", [[this.state.selectedPost.id]]);
        
        this.closeModal();
        await this.radarService.loadPosts();
    }
}

PostsPage.template = "alpha_echo.PostsPage";
registry.category("actions").add("alpha_echo.posts_client_action", PostsPage);
