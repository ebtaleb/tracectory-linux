// Main GUI logic is here

var visibleView;

function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDword(d){
	var temp =("000000000"+d.toString(16));
	return temp.substring(temp.length-8).toUpperCase();
}

function formatWord(d){
	var temp =("000000000"+d.toString(16));
	return temp.substring(temp.length-2);
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
var oldView=null;
function showView(newId){
	if(oldView != null) $(oldView).hide();
	$(newId).show();
	oldView = newId;
}

var lastMemAddr = 0;
function refreshMemoryDump(address, time){
	var params = {"address" : address, 'time' : time};	
	lastMemAddr = address;
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


function createButton(uiClass, time){
	var button = $("<div></div>");
	button.addClass( 'ui-icon');
	button.addClass( uiClass);
	button.css( {'float' : 'left' });
	return button;

}

function refreshCPUView(time){
	$.getJSON("/cpu/getInstructions", {'time' : time}).done(
		function(data){
			var output = '';
			var instrs = data['disasm'];
			for(var i = 0; i < instrs.length;i++){
				line = instrs[i];
				output += (line[0]) + "/" + formatDword(line[1]) + " " + line[2];
				//output += "<br/>";
				output += "\n";
			}	
			$("#instrContents").html(output);
			$("#cpuState").text( data['dump']);
			var curInstruction = instrs[instrs.length - 1];
			$("#curExec").html(formatDword(curInstruction[1]) + " " + htmlEntities(curInstruction[2]));
		}

	);

	$.getJSON("/memory/getRW", {'time' : time}).done(
		function(data){
			//Reads

			var buttons = $("#memButtons");
			buttons.empty();
			readHtml = ""; writeHtml ="";
			if(data['reads'].length != 0){
				readHtml = "Read:<ul>\n";
				for(i = 0; i < data['reads'].length; i++){
					var span = $("<span> </span>");
					span.attr("id",i);
					span.html( formatDword(data['reads'][i]['addr'])  + "&nbsp;");
					span.css( {'color' : '#080' , 'float' : 'left'} )
					span.append( createButton('ui-icon-circle-arrow-w', 123));
					span.append( createButton('ui-icon-circle-arrow-e', 123));
					span.append( createButton('ui-icon-arrowthick-1-w', 123));
					span.append( createButton('ui-icon-arrowthick-1-e', 123));
					buttons.append(span);
					span = null;
					prevWrite = data['reads'][i]['prevWrite'];
					readHtml += "<li class=\"readMemLink\">";
					readHtml += formatDword(data['reads'][i]['addr']);	
					if(prevWrite != null){
						readHtml += " <a href=\"javascript:moveToTime(" 
						readHtml += prevWrite + ")\">";
						readHtml += "&lt;- previous write</a>"
					}
					readHtml += "</li>\n";
				}
				readHtml += "</ul>";
			}
			//Writes
			if(data['writes'].length != 0){
				writeHtml = "Written:<ul>\n";
				for(i = 0; i < data['writes'].length; i++){

					nextRead = data['writes'][i]['nextRead'];
					writeHtml += "<li class=\"writeMemLink\">";
					writeHtml += formatDword(data['writes'][i]['addr']);	
					if(nextRead != null){
						writeHtml += " <a href=\"javascript:moveToTime(" 
						writeHtml += nextRead + ")\">";
						writeHtml += "next read -&gt;</a>"
					}

					writeHtml += "</li>\n";
				}
				writeHtml += "</ul>";
			}

			$("#memoryLinks").html(readHtml + writeHtml);
		}
	);
}



function initSlider(){
	$("#timeslider").slider();
	$.getJSON("/getInfo").done(
		function(data){
			$("#timeslider").slider("option","max",data["maxTime"]);
			for(var i = 0; i < data['traces'].length;i++){
				var name = data['traces'][i];
				$("#tracesToLoad").append("<li class=\"classy\" id=\"load_" + name + "\"><a href=\"#\">" + name + "</a></li>");
			}
			lastMemAddr = data['memDumpAddr'];
			menuInit();
			refreshMemoryDump(lastMemAddr, $("#timeslider").slider("value"));

		}
	);
	$("#timeslider").on("slidechange",
		function(event, ui){
			var val = $("#timeslider").slider("value");
			$("#lblCurTime").html(htmlEntities(val));
			refreshMemoryDump(lastMemAddr, val);
			refreshCPUView(val);	
		});


}


function memClick(address, time){
	if(time == -1) return;
	//refreshGraph(address, time);
	jumpToTime(time);
	window.open("/view/renderDataflow?address=" + escape(address) + "&time=" + escape(time));
}



function menuInit(){
	$("#menu").menubar( { select: menuSelect } );
}


function menuSelect(event, ui){
	var id = ui.item[0].id;
	if(id.substring(0,5) == "load_"){
		toLoad = id.substring(5);
		var params = {'trace' : toLoad};
		$.getJSON("/loadTrace", params).done(
			function(data){
				if(data['status'] == 'ok'){
					location.reload();
				}
			}
		);
	}else if(id == "jumpToTime"){
		var val = $("#timeslider").slider("value");
		$("#txtTargetTime").val(val);
		$("#jumpToForm").dialog( "open" );
	}else if(id == "memRWGraph"){
		$("#dlgRWGraph").dialog( "open" );
	}else if(id == "showZoom"){
		showView("#zoomView");
	}else if(id == "showCpu"){
		showView("#instrView");
	}else if(id == "showTaint"){
		showView("#taintView");
	}else if(id == "showRW"){
		showView("#rwView");
	}
	
	
	event.preventDefault();
}

function jumpToTime(newTime){
	$("#timeslider").slider("value",newTime);
}

function onClickJump(){
	var newTime = $("#txtTargetTime").val();
	jumpToTime(newTime);

}

function initTimeJumpDlg(){
	$("#jumpToForm").dialog( { 
		autoOpen: false, 
		resizable : false,
		open: function(){
		    $("#jumpToForm").keypress(function(e) {
		      if (e.keyCode == $.ui.keyCode.ENTER) {
			onClickJump();
			return false;
		      }
		    });
		},
		buttons: {
			"Jump" : onClickJump,
			"Close" : function() {
				$(this).dialog("close");
			}
		}
		} );

}


function onMemSetClick(){
	lastMemAddr = parseInt($("#txtMemAddr").val(),16);
	refreshMemoryDump(lastMemAddr, $("#timeslider").slider("value"));

}

function initMemdumpDlg(){
	$("#dlgSetMemAddr").dialog({
		autoOpen: false,
		open: function(){
		    $("#dlgSetMemAddr").keypress(function(e) {
		      if (e.keyCode == $.ui.keyCode.ENTER) {
			onMemSetClick();
			return false;
		      }
		    });
		},

		buttons: {
			"OK" : function(){	onMemSetClick();	},
			"Close" : function() { 	$(this).dialog("close"); 	}

		}
	});
	$("#btnSetAddr").click(function(){ $("#dlgSetMemAddr").dialog("open"); });

}

function initDialogs(){
	initTimeJumpDlg();
	initMemdumpDlg();
	fwdTaintDlg();
	initRwGraphDlg();
}


/////////////// Taint visualization
function fwdTaintOnClick(){
	var address = $("#txtAddress").val();
	var time = $("#txtTime").val();
	drawTaintVis(parseInt(address,16), parseInt(time));

}

function fwdTaintDlg(){
	$("#dlgForwardTaint").dialog({
		autoOpen: false,
		open: function(){
		    $("#dlgForwardTaint").keypress(function(e) {
		      if (e.keyCode == $.ui.keyCode.ENTER) {
			fwdTaintOnClick();
			return false;
		      }
		    });
		},
		modal: true,
		buttons: {
			"Trace & draw" : fwdTaintOnClick,
			"Close": function() { $(this).dialog("close"); }
		}
		
	});

}

var taintPaper;
function drawTaintVis(address, time){

	width = 1000;
	byteCount = 70;
	var paper;
	if(taintPaper != null){
		paper = taintPaper;
	}else{
		paper = new Raphael(document.getElementById("readGraphCanvas"), width, 400);
		taintPaper = paper;
	}
	
	paper.clear();
	perByteX = Math.floor(width/byteCount);
	perByteY = 5;
	fontSize = 10;
	textStartOffset = (perByteX/2) - (fontSize/2);
	for(var x=0;x<byteCount;x++){
		paper.text(x*perByteX + textStartOffset, 10, x, paper.getFont("Courier"),10).attr(
				{"text-anchor": "start"});
	}
	var params = { 'address' : address, 'time' : time};
	$.getJSON("/taint/forwardTaint", params).done(
	function(response){
		graph = response['graph'];
		dataBytes = response['data'];	
		for(var x = 0; x < dataBytes.length; x++){
			var c = String.fromCharCode(dataBytes[x]);
			paper.text(x*perByteX + textStartOffset, 
				   20, 
				   c, paper.getFont("Courier"),10).attr(
				{"text-anchor": "start"});
		}
		for(var y=0;y<graph.length;y++){
			for(var j=0;j<graph[y][0].length;j++){
				var loc = graph[y][0][j];
				paper.rect(loc*perByteX, 35+y*perByteY, perByteX,perByteY).attr(
					{"fill" : graph[y][1], "stroke" : graph[y][1]}	
				);
			}
		}

	}
	);
}


//////////// Byte-by-byte memory trace /////////////////
function rwTraceOnClick(){


	showView("#rwView");

	var address = $("#txtAddressRW").val();
	var bytes = $("#txtBytesRW").val();
	var time = $("#txtTimeRW").val();
	var cycles = $("#txtCyclesRW").val();
	var compress = $("#chkCompress").prop("checked") ? 1 : 0;

	drawRWGraph(address, parseInt(bytes), parseInt(time), parseInt(cycles), compress);
}

function openRWTraceDialog(startAddr, endAddr, startTime, endTime){
	$("#txtAddressRW").val(startAddr.toString(16));
	$("#txtBytesRW").val( endAddr - startAddr);
	$("#txtTimeRW").val(startTime);
	$("#txtCyclesRW").val(endTime - startTime);
	
	$("#dlgRWGraph").dialog( "open" );
}

function initRwGraphDlg(){
	$("#dlgRWGraph").dialog({
		autoOpen: false,
		modal: true,
		open: function(){
		    $("#dlgRWGraph").keypress(function(e) {
		      if (e.keyCode == $.ui.keyCode.ENTER) {
			rwTraceOnClick();
			return false;
		      }
		    });
		},


		buttons: {
			"Trace & draw" : rwTraceOnClick,
			"Close": function() { $(this).dialog("close"); }
		}
		
	});

}

function drawRWGraph(address, bytes, time, cycles, compress){
	var params = {
			'address' : address,
			'bytes' : bytes,
			'time' : time,
			'cycles' : cycles,
			'compress' : compress
	};
	$.getJSON("/memory/rwTrace", params).done(
	function(response){
		var events = response['graph'];
		var paper;

		if(rwPaper != null) {
			paper = rwPaper; 
		}
		else{
			paper = new Raphael(document.getElementById("rwGraphCanvas"));
			rwPaper = paper;
		}
		paper.clear();

		if(response['status'] == 'error'){
			alert(response['error']);
			return;
		}


		var rangeSize = response['rangeSize'];

		graphXOffset = 160;
		ySize = 6;
		width = graphXOffset + 10 + rangeSize * 10 + 15;
		height = 10 + events.length * ySize + 15;
		paper.setSize(width + 1, height + 1);
		for(y=0;y<events.length;y++){
			var instrInfo = events[y][0];
			var text = formatDword(instrInfo.a) + " " + instrInfo.d;
			var textObj = paper.text(0, 10 + y * ySize, text);
			textObj.attr( {'text-anchor' : 'start' , 'font-family' : 'monospace', 'font-size' : '6'});
			textObj.data("time", instrInfo.t);
			textObj.click( function() { moveToTime(this.data("time")); });
			for(i = 0; i < events[y][1].length; i++){
				x = events[y][1][i][0];
				type = events[y][1][i][1];
				paper.rect(graphXOffset + 10 + x * 10, 10 + y * ySize, 10 , ySize)
				.attr({"fill" : (type == "W") ? "#f00" : "#0f0"})
				.data("time", events[y][0])
				.click(function(){
					moveToTime(this.data("time"));
				});
			}
		}
	}
	);
	
}


function moveToTime(newTime){
	$("#timeslider").slider("value",newTime);
}
var rwPaper = null;



//////////////////////////////////////////////////////////////////////////

$ (function() {
	
	initDialogs();
	initSlider();
	$("#btnForwardTaint").button().click(
		function(event){
			$("#dlgForwardTaint").dialog("open");
			event.preventDefault();
		}
	);


	$("#timeslider").slider("value",0);

	$('#memView').mousewheel(function(event, delta, deltaX, deltaY) {
		lastMemAddr += -32 * deltaY;
		refreshMemoryDump(lastMemAddr, $("#timeslider").slider("value"));
	});

	$('#instrContents').mousewheel(function(event, delta, deltaX, deltaY) {
		if(deltaY<0){
			$("#timeslider").slider("value", $("#timeslider").slider("value") +1);
		}else{

			$("#timeslider").slider("value", $("#timeslider").slider("value") -1);
		}
	});
	showView("#zoomView");
	zoomGraphInit();

});
