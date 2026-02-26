/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";

export class SmartRadarDashboard extends Component {
    setup() {
        this.action = useService("action");
        
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

        this.radarService = useService("smart_radar.radar_service");
        this.state = useState(this.radarService.state);

        // Dummy data moved to service

        onWillStart(async () => {
            await this.loadChartJs();
            if(window.Chart) {
                window.Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
            }
        });

        onMounted(() => {
            this.initCharts();
            
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
            this.radarService.pushLog("جاهزية النظام", "محرك الاستكشاف ووحدة الصياغة الآلية في وضع التفعيل اللحظي. الاتصال نشط ومستقر.", "success");
        });

        onWillUnmount(() => {
            if (this.resizeObserver) this.resizeObserver.disconnect();
            if (this.mockInterval) clearInterval(this.mockInterval);
            this.chartInstances.forEach(c => c.destroy());
        });
    }

    async loadChartJs() {
        return new Promise((resolve, reject) => {
            if (window.Chart) { resolve(); return; }
            const script = document.createElement("script");
            script.src = "https://cdn.jsdelivr.net/npm/chart.js";
            script.onload = () => {
                window.Chart.defaults.font.family = "'Alexandria', sans-serif";
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createSparkline(ctx, data, colorHex, r, g, b) {
        let grad = ctx.createLinearGradient(0, 0, 0, 48);
        grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.25)`);
        grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.0)`);

        return new window.Chart(ctx, {
            type: 'line',
            data: {
                labels: ['1','2','3','4','5','6','7'],
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

    initCharts() {
        if (!window.Chart) return;

        // Grants discovered trend
        if(this.sparkline1.el) this.chartInstances.push(this.createSparkline(this.sparkline1.el.getContext("2d"), [1, 2, 0, 3, 2, 4, 5], '#3b82f6', 59, 130, 246));
        // Posts created trend
        if(this.sparkline2.el) this.chartInstances.push(this.createSparkline(this.sparkline2.el.getContext("2d"), [2, 4, 0, 6, 4, 8, 10], '#10b981', 16, 185, 129));
        // Match Rate trend
        if(this.sparkline4.el) this.chartInstances.push(this.createSparkline(this.sparkline4.el.getContext("2d"), [95, 96, 94, 98, 97, 98, 99], '#f59e0b', 245, 158, 11));

        // Rounded Bar Chart flow density
        if(this.barChartCanvas.el) {
            const ctxBar = this.barChartCanvas.el.getContext("2d");
            this.chartInstances.push(new window.Chart(ctxBar, {
                type: 'bar',
                data: {
                    labels: ['٨ ص', '١٠ ص', '١٢ م', '٢ م', '٤ م', '٦ م'],
                    datasets: [{
                        label: 'الموضوعات والمحتوى الملتقط',
                        data: [2, 5, 8, 12, 6, 3],
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
                    rtl: true,
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
                    labels: ['الموقع الرسمي', 'حساب منصة X'],
                    datasets: [{
                        data: [50, 50], // 50/50 dual publish
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
        this.mockInterval = setInterval(() => {
            if (this.state.isTracking) {
                this.radarService.fetchFeed();
            }
        }, Math.floor(Math.random() * 4000) + 7000);
    }

    toggleTracking() {
        this.radarService.toggleTracking();
    }

    fetchLatest() {
        this.radarService.fetchFeed();
    }
}

SmartRadarDashboard.template = "smart_radar.Dashboard";
registry.category("actions").add("smart_radar.dashboard", SmartRadarDashboard);
