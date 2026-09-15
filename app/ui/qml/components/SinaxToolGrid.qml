import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    // Child items can be passed directly or via a model
    default property alias contentData: gridFlow.data
    property int spacing: Theme.spacingL
    property int minItemWidth: 280
    property int maxColumns: 4

    // Dynamic columns computation
    readonly property int computedColumns: {
        var w = width > 0 ? width : 800;
        if (w < 580) return 1;
        if (w < 900) return 2;
        if (w < 1300) return Math.min(3, root.maxColumns);
        return Math.min(4, root.maxColumns);
    }

    // Calculated item width to fill row evenly
    readonly property real itemWidth: {
        var cols = root.computedColumns;
        var totalSpacing = (cols - 1) * root.spacing;
        return Math.max(minItemWidth, (width - totalSpacing) / cols);
    }

    implicitWidth: parent ? parent.width : 800
    implicitHeight: gridFlow.implicitHeight

    Flow {
        id: gridFlow
        anchors.fill: parent
        spacing: root.spacing
        layoutDirection: Qt.RightToLeft

        // Enforce dynamic item width on all direct children
        onChildrenChanged: {
            for (var i = 0; i < children.length; ++i) {
                var child = children[i];
                if (child && child.width !== undefined) {
                    child.width = Qt.binding(function() { return root.itemWidth; });
                }
            }
        }
    }
}
