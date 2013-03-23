/*
 * This file is provided for custom JavaScript logic that your HTML files might need.
 * Maqetta includes this JavaScript file by default within HTML pages authored in Maqetta.
 */


function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDword(d){
	var temp =("000000000"+d.toString(16));
	return temp.substring(temp.length-8);
}

var memClick = null;



require(["dojo/ready", "dojo/dom", "dojo/dom-style", "dijit/registry", "dojo/_base/xhr"], function(ready, dom, domStyle, registry, xhr){

function refreshInstructions(time){
	console.log("refreshInstructions()");
		xhr.get({
	url:"/getInstructions",
	content: {'time': time},
	handleAs:"json",
	load: function(data){

		console.log("refreshInstructions() callback");
		var disasm = data['disasm'];
		var view = dom.byId("instructionView");
		view.innerHTML = "<br/>";
		for(var i = 0; i < disasm.length; i++){
			view.innerHTML += (disasm[i][0] + "/" + disasm[i][1].toString(16) + " " + disasm[i][2]) + "<br/>";
		}

		console.log("refreshInstructions() callback finished");
		refreshMemView(lastMemAddr, time);
	}
	})

}
var lastMemAddr = 0x404050;
function memClickIn(address, time){
	refreshGraph(address,time);

	var slider = registry.byId("timeSlide");
	slider.set("value", time);
	needRefresh = true;
}

// "Publish" the function to public scope
memClick = memClickIn;

function refreshGraph(address, time){
		xhr.get({
	url:"/dataflow",
	content: {'time' : time, 'address': address},
	handleAs:"json",
	load: function(data){

	document.getElementById('canvas').innerHTML = Viz(data['graph'], "svg");

	}});


}

var delayPerRefresh = 300;
var needRefresh = true;
var refreshInProgress = false;
function doRefresh(){
	console.log("doRefresh() called");
	if(needRefresh && !refreshInProgress){
		refreshInProgress = true;
		console.log("do an actual refresh");
		var time = Math.floor(registry.byId("timeSlide").value);
		refreshInstructions(time);
		needRefresh = false;
	}
	setTimeout(doRefresh, delayPerRefresh);
}

function refreshMemView(address, time){

	console.log("refreshMem()");
	lastMemAddr = address;

	xhr.get({
	url:"/getMemJson",
	content: {'time': time, 'address': address},
	handleAs:"json",
	load: function(data){
		var bytes = data['bytes'];
		var times = data['times'];
		var hexView = dom.byId("hexView");
		var hexData = "";
		var asciiData = "";
		var mostRecentTime = -1;

		console.log("refreshMem() callback");
		for(var i = 0; i < times.length;i++)
			mostRecentTime = Math.max(mostRecentTime, times[i]);

		for(var i = 0; i < bytes.length; i++){
			if(i%8 == 0){
				if(i>0){
					hexData += "<br/>";
					asciiData += "<br/>";
				}
				hexData += formatDword(address + i) + " ";
			}
			if(bytes[i] != -1){
				hexed = bytes[i].toString(16).toUpperCase();
				if(hexed.length == 1) hexed = "0" + hexed;
			}else{
				//Unable to recover value
				hexed = "??";
			}
			style = "";
			if(times[i] == mostRecentTime){
				hexData +="<font color=\"red\">";
				asciiData +="<u>";
				style = "color: #f00; font-weight: bold;";
			}
			hexData += "<a href=\"javascript:memClick(" + (address+i) + ", " + times[i] + ");\" style=\"" + style + "\">" + hexed + "</a> ";
			asciiData += "<span style=\"" + style + "\">" + htmlEntities(String.fromCharCode(bytes[i])) + "</span>";
			if(times[i] == mostRecentTime){
				hexData += "</font>";
				asciiData += "</u>";
			}

		}
		hexView.innerHTML = hexData;
		dom.byId("asciiView").innerHTML = asciiData;
		refreshInProgress = false;
	}
	});
}


     ready(function(){
	/*refreshMemView(0x404050, 1);
	refreshGraph(0x404053,300);*/

	setTimeout(doRefresh, 200);



	var slider = registry.byId("timeSlide");
		slider.on("change", function (newValue) {
			needRefresh = true;
		});


     });
});


