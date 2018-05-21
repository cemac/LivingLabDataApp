

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