var paper;
var selectionRect;
var backgroundRect;

var startTime = -1;
var endTime = -1;
var startAddr = -1;
var endAddr = -1;

var dataTable = new Array();

function main(){
	width = 710; height = 520;
	if(paper == null)
		paper = new Raphael(document.getElementById("canvas"), width, height);
	dataTable = new Array();
	paper.clear();

	selectionRect = paper.rect(0,0,0,0).attr( {"fill" : "#00f", "opacity" : 0.5 });
	pullRows(0);
	backgroundRect = paper.rect(0,0,width, height);
	backgroundRect.mousedown( function(event) {
		selecting = true;
		console.log(event);
		selectionRect.attr( { "x" : toScreenX(event.pageX) , "y" : toScreenY(event.pageY)} );
	});
	backgroundRect.mousemove( function(event) {
		backgroundRect.toFront();

		if(selecting){
			selectionRect.attr( { "width" : toScreenX(event.pageX) - selectionRect.attr("x"), 
			"height" : toScreenY(event.pageY) - selectionRect.attr("y") });	

		}


		var x = toScreenX(event.pageX);
		var y = toScreenY(event.pageY);

		entry = toAddr(x, y);	
		if(entry.empty) return;
		$("#memInfo").html("First address: " + entry.firstAddr.toString(16));
		

	});
	backgroundRect.mouseup( function() {
		selecting = false;
		performSelection();
	});
	backgroundRect.attr( {"fill" : "#fff", "opacity" : 0});
	backgroundRect.toFront();
	

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

function toScreenX(x){ 	return x - $(document).scrollLeft() - $("#canvas").offset().left; }
function toScreenY(y){ 	return y - $(document).scrollTop() - $("#canvas").offset().top; }

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
				if( (!entry.wasRead) && !(entry.wasWritten)) {
					dataTable[addrIdx + blockNum][timeIdx].empty = true;
					continue;
				}


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

function formatDword(d){
	var temp =("000000000"+d.toString(16));
	return temp.substring(temp.length-8);
}

function formatChar(c){
	if(c<30 || c>=127)
		return ".";
	return String.fromCharCode(c);
}


function byteToHex(b){
	if(b != -1){
		hexed = b.toString(16).toUpperCase();
		if(hexed.length == 1) hexed = "0" + hexed;
	}else{
		//Unable to recover value
		hexed = "??";
	}
	return hexed;

}
function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}



var lastMemAddr = 0;
function refreshMemoryDump(address, time){
var params = {"address" : address, 'time' : time};	
$.getJSON("/memory/getMemJson", params).done(
	function(data){
		var bytes = data['bytes'];
		var times = data['times'];
		var hexData = "";
		var asciiData = "";
		var mostRecentTime = -1;

		console.log("refreshMem() callback");
		for(var i = 0; i < times.length;i++)
			mostRecentTime = Math.max(mostRecentTime, times[i]);

		for(var i = 0; i < bytes.length; i++){
			if(i%8 == 0){
				if(i>0){
					asciiData += "<br/>";
					hexData += "<br/>";
				}
				hexData += formatDword(address + i) + " ";
			}
			hexed = byteToHex(bytes[i]);
			style = "";
			if(times[i] == mostRecentTime && mostRecentTime>=0){
				hexData +="<font color=\"red\">";
				asciiData +="<u>";
				style = "color: #f00; font-weight: bold;";
			}
			hexData += "<a href=\"javascript:memClick(" + (address+i) + ", " + times[i] + ");\" style=\"" + style + "\">" + hexed + "</a> ";
			asciiData += "<span style=\"" + style + "\">" + htmlEntities(formatChar(bytes[i])) + "</span>";
			if(times[i] == mostRecentTime){
				hexData += "</font>";
				asciiData += "</u>";
			}

		}
		$("#hexView").html(hexData);
		$("#asciiView").html(asciiData);

	}
);

}



$(function () {
		main();
	      }

);
