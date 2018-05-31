function addCPCData (lats, lons, concs, binLims, colsHex) {
    var marker, iconStyle, iconColor;

    for (var i = 0; i < concs.length; i++) {
        if (concs[i] <= binLims[i]) {
            iconColor = colsHex[i];
        }
        else if (concs[i] > binLims[binLims.length - 1]) {
            iconColor = colsHex[colsHex.length - 1];
        }
        else {
            for (var j = 0; j < binLims.length - 1; j++) {
                if (concs[i] > binLims[j] && concs[i] < binLims[j + 1]) {
                    iconColor = colsHex[j + 1];
                }
            }
        }
        iconStyle = {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 6,
            strokeWeight: 1,
            strokeOpacity: 0.8,
            strokeColor: iconColor,
            fillOpacity: 0.5,
            fillColor: iconColor
        }

        marker = new google.maps.Marker({
            position: {lat: lats[i], lng: lons[i]},
            icon: iconStyle,
            clickable: false,
            map: map
        });

    }
}
