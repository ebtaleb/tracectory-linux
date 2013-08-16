var paper;
function main(){

	paper = new Raphael(document.getElementById("canvas"), 3200, 1500);
	paper.clear();
	pullRows(0);
	

}

function pullRows( blockNum){
	var params = { 'xResolution' : 50, 'yResolution' : 50, 'startBlock' : blockNum};
	perX = 5;
	perY = 5;
	if( blockNum >= params['yResolution']   )return;
	
	$.getJSON("/memory/wholeProgram", params).done(function(data){
		for(var y = 0; y < data.length;y++){
			for(var x = 0; x < data[y].length;x++){
				var entry = data[y][x];
				if(data[y][x].readCount == 0 && data[y][x].writeCount == 0) continue;
				var rect = paper.rect(x*perX, (y + blockNum) *perY, perX, perY);
				var redChar = ( entry.writeCount > 0 ? "f" : "0");
				var greenChar = ( entry.readCount > 0 ? "f" : "0");
				rect.attr( { "fill" : "#" + redChar + greenChar + "0" } )
				rect.node.info = data[y][x];
				rect.node.onmousedown = function(){
					alert("Address: " + this.info.firstAddr.toString(16)+ " time: " + this.info.firstTime);
				};
			}

		}
		pullRows(blockNum + data.length);
	
	});

}


$(function () {
		main();
	      }

);
