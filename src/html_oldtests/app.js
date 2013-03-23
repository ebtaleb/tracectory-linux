/*
 * This file is provided for custom JavaScript logic that your HTML files might need.
 * Maqetta includes this JavaScript file by default within HTML pages authored in Maqetta.
 */


function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}


require(["dojo/ready", "dojo/dom", "dojo/dom-style", "dijit/registry", "dojo/_base/xhr"], function(ready, dom, domStyle, registry, xhr){

function refreshMemView(address, time){
	xhr.get({
	url:"/getMemJson",
	content: {'time': time, 'address': address},
	handleAs:"json",
	load: function(data){
		var bytes = data['bytes'];
		var hexView = dom.byId("hexView");
		var hexData = "";
		var asciiData = "";
		for(var i = 0; i < bytes.length; i++){
			if(i%8 == 0){
				hexData += "<br/>";
				asciiData += "<br/>";
			}
			if(bytes[i] != -1){
				hexed = bytes[i].toString(16).toUpperCase();
				if(hexed.length == 1) hexed = "0" + hexed;
			}else{
				//Unable to recover value
				hexed = "??";
			}
			hexData += hexed + " ";
			asciiData += htmlEntities(String.fromCharCode(bytes[i]));
		}
		hexView.innerHTML = hexData; //"<span style=\"font: Courier\">" + hexData + "</span>";
		hexView.style.cssFloat = "left";
		dom.byId("asciiView").innerHTML = asciiData;
		dom.byId("asciiView").style.cssFloat="left";

		for(var i in data){
		console.log("key", i, "value", data[i]);
		}
	}
	});
}


     ready(function(){
         // logic that requires that Dojo is fully initialized should go here

         //Get reference to button
    	 var button = dom.byId("hexView");
		button.innerHTML = "javascript test";

		var slider = registry.byId("timeSlide");
		slider.on("change", function (newValue) {
			refreshMemView(0x404050, Math.floor(newValue));
//			alert(newValue);
		});

     });
});

