(()=>{
const s=_modelStateForSelect.toString();
return {hasLane:s.includes('laneId'),len:s.length,tail:s.slice(-600), dupDefs:(ui.match(/function _modelStateForSelect\(/g)||[]).length};})()
