function addCPCData (lats, lons, concs, binLims, colsHex) {
    var marker, iconStyle, iconColor;

    for (var i = 0; i < concs.length; i++) {
        if (concs[i] <= binLims[i]) {
            iconColor = colsHex[i];
        }
        else if (concs[i] > binLims[binLims.length - 1]) {
            iconColor = colsHex[binLims.length - 1];
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

function addMarkers(lats, lons, N=10)
{
    var startMarker = new google.maps.Marker({
        position: {lat: lats[0], lng: lons[0]},
        title: "START",
        icon: '/static/008000.png',
        map: map
    })
    var endMarker = new google.maps.Marker({
        position: {lat: lats[lats.length-1], lng: lons[lons.length-1]},
        title: "END",
        icon: '/static/FF0000.png',
        map: map
    })

    var j;
    for(var i = 1; i <= N+1; i++)
    {
        j = Math.floor(lats.length*i/(N+1));
        console.log("i: " + i + " j: " + j)
        console.log(lats[j] + ", " + lons[j])
        new google.maps.Marker({
            position: {lat: lats[j], lng: lons[j]},
            title: i.toString(),
            icon: '/static/D3D3D3.png',
            map: map
        })
    }
}