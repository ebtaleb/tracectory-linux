var mainPaper;
var selectionRect;
var backgroundRect;

var startTime = -1;
var endTime = -1;
var startAddr = -1;
var endAddr = -1;

var dataTable = new Array();

var iconsLoaded = false;

function zoomOut(){
	startTime = endTime = -1;
	startAddr = endAddr = -1;
	zoomGraphInit();
}

function zoomGraphInit(){
	width = 710; height = 520;
	if(mainPaper == null)
		mainPaper = new Raphael(document.getElementById("zoomCanvas"), width, height);
	dataTable = new Array();
	mainPaper.clear();

	selectionRect = mainPaper.rect(0,0,0,0).attr( {"fill" : "#00f", "opacity" : 0.5 });
	pullZoomGraphData(0);
	backgroundRect = mainPaper.rect(0,0,width, height);
	backgroundRect.mousedown( function(event) {
		selecting = true;
		console.log(event);
		selectionRect.attr( { "x" : toScreenX(event.pageX) , "y" : toScreenY(event.pageY)} );
	});
	backgroundRect.mousemove( onHoverBlock );
	backgroundRect.mouseup( function() {
		selecting = false;
		performSelection();
	});
	backgroundRect.attr( {"fill" : "#fff", "opacity" : 0});
	backgroundRect.toFront();

	if(!iconsLoaded){
		var p = new Raphael(document.getElementById("clockIcon"), 32, 32);
		p.clear();
		p.path(icon_clock).attr( { "fill" : "#000", "stroke" : "none" })

		var p = new Raphael(document.getElementById("clockIcon2"), 32, 32);
		p.clear();
		p.path(icon_clock).attr( { "fill" : "#000", "stroke" : "none" });

		var p = new Raphael(document.getElementById("zoomOutIcon"), 32, 32);
		p.clear();
		var path = p.path(icon_zoomout).attr( { "fill" : "#000", "stroke" : "none" });
		path.click(zoomOut);
		
		
		var p = new Raphael(document.getElementById("dbIcon"), 32, 32);
		p.clear();
		p.path(icon_db).attr( { "fill" : "#000", "stroke" : "none" });
		iconsLoaded = true;
	}	

}

function onHoverBlock(event){
	backgroundRect.toFront();

	if(selecting){
		selectionRect.attr( { "width" : toScreenX(event.pageX) - selectionRect.attr("x"), 
		"height" : toScreenY(event.pageY) - selectionRect.attr("y") });	

	}


	var x = toScreenX(event.pageX);
	var y = toScreenY(event.pageY);

	entry = toAddr(x, y);	
	if(entry.empty) return;
	$("#lblTime").html(htmlEntities(entry.firstTime + " - " + entry.lastTime));
	$("#lblAddr").text(htmlEntities(formatDword(entry.firstAddr) + " - " + formatDword(entry.lastAddr)));

}

function toAddr(x, y){
	var xIdx = ~~(x/perX);
	var yIdx = ~~(y/perY);
	if(xIdx < 0) xIdx = 0;
	if(xIdx >= dataTable.length) xIdx = dataTable.length - 1;
	if(yIdx < 0) yIdx = 0;
	if(yIdx >= dataTable[0].length) yIdx = dataTable[0].length - 1;

	return dataTable[xIdx][yIdx];
	
}

function toScreenX(x){ 	return x - $(document).scrollLeft() - $("#zoomCanvas").offset().left; }
function toScreenY(y){ 	return y - $(document).scrollTop() - $("#zoomCanvas").offset().top; }

function performSelection(){
	console.log("performSelection");
	var startEntry = toAddr( selectionRect.attr("x"), selectionRect.attr("y"));
	var endEntry = toAddr( selectionRect.attr("x") + selectionRect.attr("width") , 
			selectionRect.attr("y") + selectionRect.attr("height"));

	startTime = startEntry.firstTime;
	endTime = endEntry.lastTime;
	startAddr = startEntry.firstAddr;
	endAddr = endEntry.lastAddr;
	if(startEntry.firstTime == endEntry.firstTime || startEntry.firstAddr == endEntry.firstAddr) {
		//Only one square selected, let's show memory contents
		jumpToTime(startTime);
		refreshMemoryDump(startAddr, startTime);
		return;
	}

	mainPaper.clear();
	console.log("Calling main");
	zoomGraphInit();
}

var perX, perY;
var selecting = false;

//This fetches a block of data from server and renders it into the Raphael canvas
function pullZoomGraphData( blockNum){
	var params = { 'timeResolution' : 100, 'addrResolution' : 140, 'startBlock' : blockNum, 'startTime' : startTime, 'endTime' : endTime, 'startAddr' : startAddr, 'endAddr' : endAddr};
	perX = 5;
	perY = 5;
	selectionRect.toFront();
	if( blockNum >= params['addrResolution']   ){
		return;
	}
	
	$.getJSON("/memory/wholeProgram", params).done(function(data){
		for(var addrIdx = 0; addrIdx < data.length; addrIdx++){
			dataTable[addrIdx + blockNum] = new Array();
			for(var timeIdx = 0; timeIdx < data[addrIdx].length;timeIdx++){
				var entry = data[addrIdx][timeIdx];
				dataTable[addrIdx + blockNum][timeIdx] = entry;
				if( (!entry.wasRead) && !(entry.wasWritten)) {
					dataTable[addrIdx + blockNum][timeIdx].empty = true;
					continue;
				}


				var xPosition = (addrIdx + blockNum) * perX;
				var yPosition = timeIdx * perY;
				var rect = mainPaper.rect(xPosition, yPosition, perX, perY);
				var redChar = ( entry.wasWritten  ? "f" : "0");
				var greenChar = ( entry.wasRead  ? "f" : "0");
				rect.attr( { "fill" : "#" + redChar + greenChar + "0" } )
				rect.node.info = entry;
				rect.node.positionY = yPosition;
				rect.node.positionX = xPosition;
			}

		}
		if(data.length != 0)
			pullZoomGraphData(blockNum + data.length);
	
	});

}



