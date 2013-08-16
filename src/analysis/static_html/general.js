var paper;
var selectionRect;
var backgroundRect;

var startTime = -1;
var endTime = -1;
var startAddr = -1;
var endAddr = -1;

function main(){
	width = 2500; height = 1200;
	paper = new Raphael(document.getElementById("canvas"), width, height);
	paper.clear();

	selectionRect = paper.rect(10,10,100,100).attr( {"fill" : "#00f", "opacity" : 0.5 });
	pullRows(0);
	backgroundRect = paper.rect(0,0,width, height);
	backgroundRect.mousedown( function(event) {
		selecting = true;
		selectionRect.attr( { "x" : event.pageX , "y" : event.pageY} );
	});
	backgroundRect.mousemove( function(event) {
		backgroundRect.toFront();
		if(selecting){
			selectionRect.attr( { "width" : event.pageX - selectionRect.attr("x"), "height" : event.pageY - selectionRect.attr("y") });	
		}
	});
	backgroundRect.mouseup( function() {
		selecting = false;
		performSelection();
	});
	backgroundRect.attr( {"fill" : "#fff", "opacity" : 0});
	backgroundRect.toFront();
	

}

var dataTable = new Array();
function toAddr(x, y){
	var xIdx = ~~(x/perX);
	var yIdx = ~~(y/perY);
	if(xIdx < 0) xIdx = 0;
	if(xIdx >= dataTable.length) xIdx = dataTable.length - 1;
	if(yIdx < 0) yIdx = 0;
	if(yIdx >= dataTable[0].length) yIdx = dataTable[0].length - 1;

	return dataTable[xIdx][yIdx];
	
}

function performSelection(){
	var startEntry = toAddr( selectionRect.attr("x"), selectionRect.attr("y"));
	var endEntry = toAddr( selectionRect.attr("x") + selectionRect.attr("width") , 
			selectionRect.attr("y") + selectionRect.attr("height"));

	startTime = startEntry.firstTime;
	endTime = endEntry.firstTime;
	startAddr = startEntry.firstAddr;
	endAddr = endEntry.firstAddr;
	paper.clear();
	console.log("Calling main");
	main();
}

var perX, perY;
var selecting = false;
function pullRows( blockNum){
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
				if( (!entry.wasRead) && !(entry.wasWritten)) continue;

				var xPosition = (addrIdx + blockNum) * perX;
				var yPosition = timeIdx * perY;
				var rect = paper.rect(xPosition, yPosition, perX, perY);
				var redChar = ( entry.wasWritten  ? "f" : "0");
				var greenChar = ( entry.wasRead  ? "f" : "0");
				rect.attr( { "fill" : "#" + redChar + greenChar + "0" } )
				rect.node.info = entry;
				rect.node.positionY = yPosition;
				rect.node.positionX = xPosition;
			}

		}
		pullRows(blockNum + data.length);
	
	});

}


$(function () {
		main();
	      }

);
