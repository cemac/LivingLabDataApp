function addCPCData (lats, lons, concs, binLims, colsHex) {
    var marker, iconStyle, iconColor;

    for (var i = 0; i < concs.length; i++) {

        var iconColor = getColor(concs[i], binLims, colsHex);

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

function addCPCLines (lats, lons, concs, binLims, colsHex) {

    for (var i = 0; i < lats.length-1; i++)
    {
        // Uses a javascript closure to make each infowindow have different data (position, content)
        // without the closure, there is only one content and position
        ( function() {

                   // get average concentration between the points
            var meanConc = Math.ceil((concs[i] + concs[i+1])/2);
            var midPoint = [
                (lats[i] + lats[i+1]) / 2,
                (lons[i] + lons[i+1]) / 2
            ];

            var color = getColor(meanConc, binLims, colsHex);

            var tail = new google.maps.LatLng(lats[i],lons[i]);
            var head = new google.maps.LatLng(lats[i+1],lons[i+1]);

            var lineCoordinates = [tail, head];

            var polyline = new google.maps.Polyline({
              path: lineCoordinates,
              strokeColor: color,
              strokeOpacity: 0.6,
              strokeWeight: 7,
              map: map
            });

            var content = meanConc.toString();
            var position = {lat: midPoint[0], lng: midPoint[1]};
            var clickFunction = function(content, position) {
                var infoWindow = new google.maps.InfoWindow({
                    content: content
                })
                infoWindow.setPosition(position);
                infoWindow.open(map);
            }

            google.maps.event.addListener(polyline, 'click', function(event){
                clickFunction(content, position);
            })
        }())
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

function getColor(conc, binLims, colsHex)
{
    if (conc <= binLims[0]) {
        return colsHex[0];
    }
    else if (conc > binLims[binLims.length - 1]) {
        return colsHex[binLims.length - 1];
    }
    else {
        for (var j = 0; j < binLims.length - 1; j++) {
            if (conc > binLims[j] && conc < binLims[j + 1]) {
                return colsHex[j + 1];
            }
        }
    }
}