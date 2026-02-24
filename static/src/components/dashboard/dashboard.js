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

        // Custom Grant Tracking State
        this.state = useState({
            isTracking: true,
            isLoading: false,
            monitoredAccounts: 350,
            grantsDiscovered: 4,
            publishedToday: 8, // 4 to X + 4 to Website
            matchRate: 98,
            feed: [],
            logs: []
        });

        // ARABIC DATA - NGO/Donors specific context
        this.dummyTexts = [
            { 
                donor: "@Alwaleed_Philan",
                raw: "تعلن مؤسسة الوليد للإنسانية عن فتح باب التقديم للحصول على تمويل مشاريع الإسكان وتنمية المجتمع لعام ٢٠٢٤ عبر البوابة الإلكترونية. آخر موعد للتقديم نهاية الشهر.", 
                ai: "إعلان استراتيجي: نُعلم شركاءنا بفتح نافذة التمويل لمشاريع الإسكان وتنمية المجتمع التابعة لمؤسسة الوليد للإنسانية (دورة 2024). يُرجى الاطلاع على المحددات والمعايير لضمان استيفاء الشروط وتوثيق الملفات قبل الموعد. [المرجع الرسمي]" 
            },
            { 
                donor: "@USAIDMiddleEast",
                raw: "USAID announces $5 million in new grant funding for climate resilience initiatives in the MENA region. Seeking local partners and NGOs.", 
                ai: "مبادرة دولية: أطلقت الوكالة الأمريكية للتنمية الدولية محفظة دعم بقيمة 5 ملايين دولار مخصصة لبرامج الاستدامة والمناخ في الشرق الأوسط. ندعو كافة الجهات المعنية لمراجعة الآليات وبناء الشراكات. [الوثيقة الرسمية]" 
            },
            { 
                donor: "@KSRelief",
                raw: "يطلق مركز الملك سلمان للإغاثة والأعمال الإنسانية برنامج تمويل الشراكات لدعم المنظمات الصحية والتعليمية في الدول النامية. للمشاركة تفضل بالتسجيل.", 
                ai: "فرصة شراكة إنسانية: أقر مركز الملك سلمان للإغاثة برنامجه الجديد لتمويل الشراكات الفاعلة في قطاعي الصحة والتعليم. تتوفر لدينا الآن إرشادات التسجيل ونماذج حوكمة التمويل للجهات المهتمة بالشراكة التشغيلية. [دليل البرنامج]" 
            },
            { 
                donor: "@isdb_stories",
                raw: "يسر البنك الإسلامي للتنمية دعوة المبتكرين للتقديم على صندوق دعم الاستدامة والابتكار لعام ٢٠٢٤.", 
                ai: "دعوة تقديم: يعلن البنك الإسلامي للتنمية عن إطلاق صندوق المستجدات التمويلية لدعم الابتكار. نوفر لعملائنا تحليلاً دقيقاً لمتطلبات الصندوق لضمان التنافسية ورفع موثوقية العروض التقنية والمجتمعية. [رابط الاستعلام]" 
            }
        ];

        this.dummyLogs = [
            { tag: "مسح المعطيات", msg: "الفحص الدوري الشامل للكيانات النشطة.. لم تُرصد مستجدات ذات صلة في الدورة الحالية.", type: "info" },
            { tag: "ترصد فرص", msg: "تم تسجيل مبادرة مستجدة مطابقة لمعايير الاستهداف الاستراتيجية المتفق عليها.", type: "success" },
            { tag: "المعالجة (AI)", msg: "يتم تفعيل الخوارزمية اللغوية لإنتاج الصياغة المعتمدة لضمان أقصى موثوقية ممكنة (معدل: 99%).", type: "primary" },
            { tag: "اعتماد النشر", msg: "المزامنة مكتملة؛ تم توجيه المادة المعالجة نحو قنوات النشر المعتمدة (WordPress و X).", type: "success" },
            { tag: "إدارة الأحمال", msg: "تأخير طلب الاستعلام برمجيا لتبادل البيانات حفاظا على الاستقرار والسياسات (Rate Limit).", type: "warning" }
        ];

        onWillStart(async () => {
            await this.loadChartJs();
            if(window.Chart) {
                window.Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
            }
        });

        onMounted(() => {
            this.initCharts();
            this.startMockFeed();
            this.addMockFeedItem(0); // init specific load
            this.pushLog("جاهزية النظام", "محرك الاستكشاف ووحدة الصياغة الآلية في وضع التفعيل اللحظي. الاتصال نشط ومستقر.", "success");
        });

        onWillUnmount(() => {
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
                window.Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
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
                        label: 'إعلانات التمويل الملتقطة',
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
                this.addMockFeedItem();
            }
        }, Math.floor(Math.random() * 4000) + 7000);
    }

    pushLog(tag, message, type) {
        const timeString = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        this.state.logs = [{ id: Date.now() + Math.random(), time: timeString, tag, message, type }, ...this.state.logs].slice(0, 8);
    }

    addMockFeedItem(indexOverride = -1) {
        let template;
        if (indexOverride >= 0 && indexOverride < this.dummyTexts.length) {
            template = this.dummyTexts[indexOverride];
        } else {
            template = this.dummyTexts[Math.floor(Math.random() * this.dummyTexts.length)];
        }
        
        const timeString = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });

        const newItem = {
            id: Date.now() + Math.random(),
            time: timeString,
            donor: template.donor,
            original: template.raw,
            rewritten: template.ai,
            tweetLink: "https://your-website.com/new-grant-post"
        };

        this.state.feed = [newItem, ...this.state.feed].slice(0, 6);
        
        // Log the discovery -> rewrite -> publish sequence naturally
        this.pushLog("تحديث تشغيلي", `رصد نشاط بيانات صادرة عن معرّف ${template.donor}.`, "info");
        setTimeout(() => this.pushLog("تدخل المعالج (AI)", `يجري تطبيق معايير الصياغة المؤسسية والتهيئة للنشر...`, "primary"), 800);
        setTimeout(() => {
            this.pushLog("المزامنة الآلية", `تمت المصادقة وتصدير المحتوى بنجاح عبر البوابات الرسمية (Web & X).`, "success");
            this.state.grantsDiscovered += 1;
            this.state.publishedToday += 2; // Web + X
        }, 1800);
    }

    toggleTracking() {
        this.state.isTracking = !this.state.isTracking;
        this.pushLog("إجراء إداري", this.state.isTracking ? "تم تفعيل محرك الاستكشاف الشامل." : "تعليق المهام الاستكشافية وعمليات الفحص.", "warning");
    }

    fetchLatest() {
        this.state.isLoading = true;
        setTimeout(() => {
            if(this.state.isTracking) this.addMockFeedItem();
            this.state.isLoading = false;
        }, 800);
    }
}

SmartRadarDashboard.template = "smart_radar.Dashboard";
registry.category("actions").add("smart_radar.dashboard", SmartRadarDashboard);
