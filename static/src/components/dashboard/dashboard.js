/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class SmartRadarDashboard extends Component {
    /** Expose _t to the OWL template context */
    get _t() { return _t; }

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        
        this.barChartCanvas = useRef("barChartCanvas");
        this.gaugeChartCanvas = useRef("gaugeChartCanvas");
        this.sparkline1 = useRef("sparkline1");
        this.sparkline2 = useRef("sparkline2");
        this.sparkline4 = useRef("sparkline4"); // 3 is static text now
        
        this.chartInstances = [];
        this.mockInterval = null;
        this.dashboardRef = useRef("dashboardMain");
        this.resizeObserver = null;
        this.resizeHandler = () => {
            this.chartInstances.forEach(c => c.resize());
        };

        this.radarService = useService("alpha_echo.radar_service");
        this.radarState = useState(this.radarService.state);

        // Dummy data moved to service

        onWillStart(async () => {
            // Chart.js is pre-bundled as a local static asset — no CDN load needed
            if(window.Chart) {
                window.Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
            }
        });

        onMounted(async () => {
            // Load actual data from backend
            await this.radarService.fetchConfig();
            await this.radarService.loadTargets();

            let metrics = null;
            try {
                metrics = await this.orm.call("alpha.echo.dashboard", "get_dashboard_metrics", []);
                this.radarState.grantsDiscovered = metrics.posts_today;
                this.radarState.publishedToday = metrics.posts_published;
                this.radarState.monitoredAccounts = metrics.targets_active;
                this.radarState.matchRate = metrics.posts_total > 0 ? Math.round((metrics.posts_published / metrics.posts_total) * 100) : 0;
            } catch (error) {
                console.error("Failed to load metrics", error);
            }

            this.initCharts(metrics);
            
            // Modern ResizeObserver for perfect "live" responsiveness
            if (this.dashboardRef.el) {
                this.resizeObserver = new ResizeObserver(() => {
                    this.chartInstances.forEach(c => {
                        if (c) {
                            c.resize();
                            c.update('none');
                        }
                    });
                });
                this.resizeObserver.observe(this.dashboardRef.el);
            }

            this.startMockFeed();
            this.radarService.pushLog(_t("System Readiness"), _t("Exploration engine and AI formulation unit are in real-time activation mode. Connection is active and stable."), "success");
        });

        onWillUnmount(() => {
            if (this.resizeObserver) this.resizeObserver.disconnect();
            if (this.mockInterval) clearInterval(this.mockInterval);
            this.chartInstances.forEach(c => c.destroy());
        });
    }

    get isRTL() { return localization.direction === "rtl"; }

    get trackingBtnLabel() {
        if (this.radarState.isTracking) {
            return _t("Pause Monitoring");
        }
        return _t("Start Exploration");
    }


    createSparkline(ctx, labels, data, colorHex, r, g, b) {
        let grad = ctx.createLinearGradient(0, 0, 0, 48);
        grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.25)`);
        grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.0)`);

        return new window.Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    borderColor: colorHex,
                    backgroundColor: grad,
                    fill: true,
                    borderWidth: 3, // Thicker premium lines
                    tension: 0.5, // Extremely smooth curves
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false } },
                layout: { padding: 0 }
            }
        });
    }

    initCharts(metrics) {
        if (!window.Chart) return;

        const chartData = metrics && metrics.chart_data.length > 0 ? metrics.chart_data : [0,0,0,0,0,0,0];
        const chartLabels = metrics && metrics.chart_labels.length > 0 ? metrics.chart_labels : ['1','2','3','4','5','6','7'];

        // Grants discovered trend
        if(this.sparkline1.el) this.chartInstances.push(this.createSparkline(this.sparkline1.el.getContext("2d"), chartLabels, chartData, '#3b82f6', 59, 130, 246));
        // Posts created trend
        if(this.sparkline2.el) this.chartInstances.push(this.createSparkline(this.sparkline2.el.getContext("2d"), chartLabels, chartData, '#10b981', 16, 185, 129));
        // Match Rate trend
        if(this.sparkline4.el) this.chartInstances.push(this.createSparkline(this.sparkline4.el.getContext("2d"), chartLabels, chartData, '#f59e0b', 245, 158, 11));

        // Rounded Bar Chart flow density
        if(this.barChartCanvas.el) {
            const ctxBar = this.barChartCanvas.el.getContext("2d");
            this.chartInstances.push(new window.Chart(ctxBar, {
                type: 'bar',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        label: _t('Topics & Captured Content'),
                        data: chartData,
                        backgroundColor: [
                            '#818cf8', '#6366f1', '#4f46e5', '#4338ca', '#3730a3', '#312e81'
                        ], // Beautiful sequential colors
                        borderRadius: 8,
                        borderSkipped: false,
                        barThickness: 30,
                        hoverBackgroundColor: '#f59e0b'
                    }]
                },
                options: {
                    animation: {
                        duration: 2000,
                        easing: 'easeOutQuart'
                    },
                    responsive: true,
                    maintainAspectRatio: false,
                    rtl: localization.direction === "rtl",
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false, drawBorder: false }, ticks: { color: '#94a3b8' } },
                        y: { display: false, grid: { display: false } }
                    }
                }
            }));
        }

        // Dual Destination Gauge
        if(this.gaugeChartCanvas.el) {
            const ctxGauge = this.gaugeChartCanvas.el.getContext("2d");
            this.chartInstances.push(new window.Chart(ctxGauge, {
                type: 'doughnut',
                data: {
                    labels: [_t('Official Website'), _t('X Account')],
                    datasets: [{
                        data: [metrics && metrics.posts_published > 0 ? metrics.posts_published : 1, metrics && metrics.posts_published > 0 ? metrics.posts_published : 1], 
                        backgroundColor: ['#4f46e5', '#1da1f2'],
                        borderWidth: 0,
                        hoverOffset: 6,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '82%',
                    plugins: { 
                        legend: { display: false },
                        tooltip: { enabled: true } 
                    },
                    animation: {
                        duration: 2000,
                        easing: 'easeOutQuart'
                    }
                }
            }));
        }
    }

    startMockFeed() {
        // High-frequency auto-fetch removed to protect user budget! 🚨
        // Scans should only triggered manually or by background cron.
    }

    toggleTracking() {
        this.radarService.toggleTracking();
    }

    openSettings() {
        this.action.doAction("alpha_echo_action_config");
    }
}

SmartRadarDashboard.template = "alpha_echo.Dashboard";
registry.category("actions").add("alpha_echo.dashboard", SmartRadarDashboard);
