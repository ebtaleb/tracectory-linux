// Main GUI logic is here


function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDword(d){
	var temp =("000000000"+d.toString(16));
	return temp.substring(temp.length-8);
}

function formatChar(c){
	if(c<30 || c>=120)
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
			if(times[i] == mostRecentTime){
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
	$("#timeJump").button().click(function(event){

		var val = $("#timeslider").slider("value");
		$("#txtTargetTime").val(val);
		$("#jumpToForm").dialog( "open" );
		event.preventDefault();
	});

}


function memClick(address, time){
	refreshGraph(address, time);
	$("#timeslider").slider("value",time);
}

function fixSize(){
	alert("fixd" + $("#graph").height());
}

function refreshGraph(address, time){
	var params =  {'time' : time, 'address': address};
	$.getJSON("/dataflow", params).done(
	 function(data){
		var svg = Viz(data['graph'], "svg");
		svg = svg.replace(new RegExp("width=\".*\"","gm"),"width=\"100%\"");
		svg = svg.replace(new RegExp("height=\".*\"","gm"),"height=\"100%\"");
		//document.getElementByID("graphView").
		$("#graph").html(svg);
		$("#graphView").width($("#graph").width() + 100);
		$("#graphView").height($("#graph").height());


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
}


var readGraphPaper;
function initReadGraph(){

	width = 1000;
	byteCount = 70;
	var paper = new Raphael(document.getElementById("readGraphCanvas"), width, 400);
	readGraphPaper = paper;
	
	perByteX = Math.floor(width/byteCount);
	perByteY = 5;
	$.getJSON("/forwardTaint", {}).done(
	function(data){
		for(var y=0;y<data.length;y++){
			for(var j=0;j<data[y][0].length;j++){
				var loc = data[y][0][j];
				console.log(loc);
				paper.rect(loc*perByteX, y*perByteY, perByteX,perByteY).attr(
					{"fill" : data[y][1], "stroke" : data[y][1]}	
				);
			}
		}

	}
);
	}

function init(){
	initReadGraph();
	refreshMemory(lastMemAddr, 0);
}

$ (function() {
	
	$("#menu").menubar( { select: select } );
	initMenu();
	//$( "#graphView" ).draggable().resizable({});
	//$("#graphView").scroll();
	//$( "#memView").resizable();
	//$( "#instrView").draggable().resizable();
	$("#accordion").accordion();
	initSlider();

	setTimeout(init, 300);
});
