// Main GUI logic is here


function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDword(d){
	var temp =("000000000"+d.toString(16));
	return temp.substring(temp.length-8);
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


var lastMemAddr = 2771222;
function refreshMemory(address, time){
var params = {"address" : address, 'time' : time};	
$.getJSON("/getMemJson", params).done(
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



function refreshInstructions(time){
	$.getJSON("/getInstructions", {'time' : time}).done(
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
			$("#cpuState").text(data['dump']);
			$("#cpuState2").text(data['dump2']);
		}

	);
}



function updateSliderFromDialog(){
	var newTime = $("#txtTargetTime").val();
	$("#timeslider").slider("value",newTime);

}

function initSlider(){
	$("#timeslider").slider();
	$.getJSON("/getInfo").done(
		function(data){
			$("#timeslider").slider("option","max",data["maxTime"]);
			lastMemAddr = data['memDumpAddr'];
		}
	);
	$("#timeslider").on("slidechange",
		function(event, ui){
			var val = $("#timeslider").slider("value");
			refreshMemory(lastMemAddr, val);
			refreshInstructions(val);	
		});

	//The "jump to a certain time" form

	$("#timeJump").button().click(function(event){

		var val = $("#timeslider").slider("value");
		$("#txtTargetTime").val(val);
		$("#jumpToForm").dialog( "open" );
		event.preventDefault();
	});

}


function memClick(address, time){
	if(time == -1) return;
	refreshGraph(address, time);
	$("#timeslider").slider("value",time);
}

function refreshGraph(address, time){
	var params =  {'time' : time, 'address': address};
	$.getJSON("/dataflow", params).done(
	 function(data){
		$("#accordion").accordion( { active: 3});
		var svg = Viz(data['graph'], "svg");
		svg = svg.replace(new RegExp("width=\".*\"","gm"),"width=\"100%\"");
		$("#graph").html(svg);

	});


}

function initMenu(){
}


function select(event, ui){
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
	}
	event.preventDefault();
}


function init(){
	//initReadGraph();
	$("#timeslider").slider("value",0);
}

function initDialogs(){
	$("#jumpToForm").dialog( { 
		autoOpen: false, 
		resizable : false,
		open: function(){
		    $("#jumpToForm").keypress(function(e) {
		      if (e.keyCode == $.ui.keyCode.ENTER) {
			updateSliderFromDialog();
			return false;
		      }
		    });
		},
		buttons: {
			"Jump" : updateSliderFromDialog,
			"Close" : function() {
				$(this).dialog("close");
			}
		}
		} );

	$("#dlgSetMemAddr").dialog({
		autoOpen: false,
		buttons: {
			"OK" : function(){
				lastMemAddr = parseInt($("#txtMemAddr").val(),16);
				refreshMemory(lastMemAddr, $("#timeslider").slider("value"));
			},
			"Close" : function() { 	$(this).dialog("close"); 	}

		}
	});
	$("#btnSetAddr").click(function(){ $("#dlgSetMemAddr").dialog("open"); });
	fwdTaintDlg();
}


// forward taint

function fwdTaintOnClick(){
	var address = $("#txtAddress").val();
	var time = $("#txtTime").val();
	drawReadGraph(parseInt(address,16), parseInt(time));

}

function fwdTaintDlg(){
	$("#dlgForwardTaint").dialog({
		autoOpen: false,
		modal: true,
		buttons: {
			"Trace & draw" : fwdTaintOnClick,

			"Close": function() { $(this).dialog("close"); }
		}
		
	});

}

var readGraphPaper;
function drawReadGraph(address, time){

	width = 1000;
	byteCount = 70;
	var paper;
	if(readGraphPaper != null){
		paper = readGraphPaper;
	}else{
		paper = new Raphael(document.getElementById("readGraphCanvas"), width, 400);
		readGraphPaper = paper;
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
	$.getJSON("/forwardTaint", params).done(
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

var rwPaper = null;
function drawRWGraph(){
	$.getJSON("/dbg", {'address' : -1 }).done(
	function(response){
		var events = response;
		var paper;
		width = events.length * 10 + 5;
		height = events.length * 3 + 5;
		if(rwPaper != null) {paper = rwPaper; }
		else{
			paper = new Raphael(document.getElementById("rwGraphCanvas"), width, height);
			rwPaper = paper;
		}


		for(y=0;y<events.length;y++){
			for(i = 0; i < events[y][1].length; i++){
				x = events[y][1][i][0] - 0x2a48e0;
				type = events[y][1][i][1];
				paper.rect(x * 10, y * 3, 10 , 3).attr(
					{"fill" : (type == "W") ? "#f00" : "#eee"}
				);
			}
		}
	}
	);
	
}

$ (function() {
	
	$("#menu").menubar( { select: select } );
	initMenu();
	//$( "#graphView" ).draggable().resizable({});
	//$("#graphView").scroll();
	//$( "#memView").resizable();
	//$( "#instrView").draggable().resizable();
	$("#accordion").accordion();
	initDialogs();
	initSlider();
	$("#btnForwardTaint").button().click(
		function(event){
			$("#dlgForwardTaint").dialog("open");
			event.preventDefault();
		}
	);

	$("#btnRW").button().click(
		function(event){
			//$("#dlgForwardTaint").dialog("open");
			drawRWGraph();
			event.preventDefault();
		}

	);

	setTimeout(init, 300);
});
