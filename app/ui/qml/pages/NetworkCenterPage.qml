import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    Rectangle {
        anchors.fill: parent
        color: Theme.background
        z: -1
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentCol.implicitHeight + Theme.spacing2XL
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        ColumnLayout {
            id: contentCol
            width: Math.min(parent.width - Theme.spacingXL * 2, 1280)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacingL

            // 1. Page Header with Breadcrumbs & Action
            SinaxPageHeader {
                Layout.fillWidth: true
                title: "مركز الشبكة والإنترنت والاتصالات"
                subtitle: "مراقبة الاتصال الحي، قياس السرعة، تشخيص الأعطال (Network Doctor)، والمشاركة المحلية."
                iconName: "network"
                breadcrumbCurrent: "الشبكة والإنترنت"
                actionText: "تشخيص شامل للاتصال ←"
                onActionClicked: networkController.runDoctorDiagnostics()
            }

            // 2. Network Overview Cards (3 Vitals Cards)
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                SinaxCard {
                    Layout.fillWidth: true
                    title: "حالة اتصال الإنترنت"
                    value: networkController.isConnected ? "متصل بالإنترنت" : "غير متصل"
                    subtitle: networkController.adapterName
                    iconName: "network"
                    accentColor: networkController.isConnected ? Theme.success : Theme.error
                }

                SinaxCard {
                    Layout.fillWidth: true
                    title: "عنوان الشبكة المحلية (IP)"
                    value: networkController.localIp
                    subtitle: "البوابة الافتراضية: " + networkController.gateway
                    iconName: "lan"
                    accentColor: Theme.primary
                }

                SinaxCard {
                    Layout.fillWidth: true
                    title: "خوادم أسماء النطاقات (DNS)"
                    value: networkController.dnsServer
                    subtitle: "استجابة طبيعية وآمنة"
                    iconName: "shield"
                    accentColor: Theme.info
                }
            }

            // 3. Interactive Speed Test Card
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 180
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "اختبار سرعة الإنترنت الحقيقي (Speed Test)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSectionTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Item { Layout.fillWidth: true }

                        SinaxButton {
                            text: networkController.isTestingSpeed ? "جاري القياس..." : "بدء اختبار السرعة ▶"
                            variant: "primary"
                            loading: networkController.isTestingSpeed
                            onClicked: networkController.startSpeedTest()
                        }
                    }

                    // Progress bar
                    SinaxProgress {
                        Layout.fillWidth: true
                        value: networkController.speedProgress
                        barColor: Theme.primary
                        showPercent: false
                    }

                    // Metrics Row
                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacing2XL

                        ColumnLayout {
                            spacing: 2
                            Text { text: "سرعة التنزيل (Download)"; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                            Text { text: networkController.downloadMbps > 0 ? String(networkController.downloadMbps) + " Mbps" : "—"; font.pixelSize: Theme.fontHeader; font.bold: true; color: Theme.primary }
                        }

                        ColumnLayout {
                            spacing: 2
                            Text { text: "سرعة الرفع (Upload)"; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                            Text { text: networkController.uploadMbps > 0 ? String(networkController.uploadMbps) + " Mbps" : "—"; font.pixelSize: Theme.fontHeader; font.bold: true; color: Theme.info }
                        }

                        ColumnLayout {
                            spacing: 2
                            Text { text: "زمن الاستجابة (Ping)"; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                            Text { text: String(networkController.pingMs) + " ms"; font.pixelSize: Theme.fontSectionTitle; font.bold: true; color: Theme.textPrimary }
                        }

                        ColumnLayout {
                            spacing: 2
                            Text { text: "التذبذب (Jitter)"; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                            Text { text: String(networkController.jitterMs) + " ms"; font.pixelSize: Theme.fontSectionTitle; font.bold: true; color: Theme.textPrimary }
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: networkController.speedPhase
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.bold: true
                            color: Theme.primary
                        }
                    }
                }
            }

            // 4. Network Doctor Diagnostics
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: docCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: docCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "طبيب الشبكة (Network Doctor) — تسلسل فحص الاتصال"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSectionTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Item { Layout.fillWidth: true }

                        SinaxBadge {
                            text: networkController.isDoctorRunning ? "جاري الفحص..." : "الفحص مكتمل"
                            variant: networkController.isDoctorRunning ? "warning" : "success"
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingM

                        Repeater {
                            model: networkController.doctorResults

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: 74
                                radius: Theme.radiusSmall
                                color: Theme.surface2
                                border.color: modelData.status === "pass" ? Theme.success : Theme.warning
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.spacingS
                                    spacing: 4

                                    RowLayout {
                                        Layout.fillWidth: true
                                        layoutDirection: Qt.RightToLeft
                                        Text { text: modelData.name; font.pixelSize: Theme.fontXS; font.bold: true; color: Theme.textPrimary; Layout.fillWidth: true; elide: Text.ElideRight }
                                        SinaxIcon {
                                            iconName: modelData.status === "pass" ? "check" : "warning"
                                            size: Theme.iconSmall
                                            color: modelData.status === "pass" ? Theme.success : Theme.warning
                                        }
                                    }

                                    Text { text: modelData.detail; font.pixelSize: Theme.fontXS; color: Theme.textSecondary }
                                }
                            }
                        }
                    }
                }
            }

            // 5. SINAX Local Share & Transfer Card
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: shareCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: shareCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "المشاركة المحلية السريعة (SINAX Share)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSectionTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Item { Layout.fillWidth: true }

                        SinaxBadge {
                            text: "خادم محلي نشط"
                            variant: "info"
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingL

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingS

                            Text {
                                text: "أرسل واستقبل الملفات بين حاسوبك والهاتف أو الحواسيب الأخرى على نفس شبكة الـ Wi-Fi بدون كابلات أو إنترنت وبأقصى سرعة للشبكة المحلية."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                color: Theme.textSecondary
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            SinaxInfoRow {
                                Layout.fillWidth: true
                                label: "عنوان الرابط المباشر:"
                                value: networkController.shareUrl
                            }

                            SinaxInfoRow {
                                Layout.fillWidth: true
                                label: "رمز الأمان السريع:"
                                value: networkController.shareCode
                            }
                        }

                        // QR Code Placeholder Card
                        Rectangle {
                            width: 120
                            height: 120
                            radius: Theme.radiusSmall
                            color: "#FFFFFF"
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                SinaxIcon {
                                    iconName: "qr_code"
                                    size: 64
                                    color: "#0F172A"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "امسح الرمز للاتصال"
                                    font.pixelSize: 10
                                    color: "#475569"
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}
