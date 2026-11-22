(function(){let e,t=Promise.resolve();async function n(e){let t=new URL(e),n=new URL(`pyodide/`,t),{loadPyodide:r}=await import(
/* @vite-ignore */
new URL(`pyodide.mjs`,n).href),i=await r({indexURL:n.href}),a=await fetch(t);if(!a.ok)throw Error(`Could not download the browser game manifest.`);let o=await a.json(),s=o.files?.[0];if(o.version!==1||o.files?.length!==1||s?.url!==`python.zip`||s.mount!==`/app`||!/^[a-f0-9]{64}$/.test(s.sha256))throw Error(`Invalid browser game manifest.`);let c=await fetch(new URL(s.url,t));if(!c.ok)throw Error(`Could not download the browser game engine.`);let l=await c.arrayBuffer(),u=new Uint8Array(await crypto.subtle.digest(`SHA-256`,l));if(Array.from(u,e=>e.toString(16).padStart(2,`0`)).join(``)!==s.sha256||l.byteLength!==s.bytes)throw Error(`The browser engine archive failed verification.`);return await i.loadPackage([`pydantic`,`pyyaml`]),i.unpackArchive(l,`zip`,{extractDir:`/app`}),await i.runPythonAsync(`
import sys
from pathlib import Path
sys.path.insert(0, '/app')
from backend.browser_bridge import BrowserBridge
_browser_bridge = BrowserBridge(Path('/app/seasons'))
`),i}self.addEventListener(`message`,({data:r})=>{t=t.then(async()=>{try{e??=n(r.manifestUrl);let t=await e;t.globals.set(`_browser_method`,r.method),t.globals.set(`_browser_path`,r.path),t.globals.set(`_browser_body`,r.body);let i=t.runPython(`_browser_bridge.request(_browser_method, _browser_path, _browser_body)`);self.postMessage({id:r.id,result:JSON.parse(i)})}catch(e){self.postMessage({id:r.id,error:`Could not run the browser game: ${e.message}`})}})})})();