export default function Settings() {
  return (
    <div className="p-6 w-full">
      <h1 className="text-3xl font-bold mb-6">Settings</h1>
      
      <div className="bg-gray-800 rounded-lg p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold mb-3">Dashboard Preferences</h2>
          <p className="text-gray-400">Configure your dashboard settings here.</p>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Auto-refresh Interval</label>
            <select className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <option>10 seconds</option>
              <option>30 seconds</option>
              <option>1 minute</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Map Theme</label>
            <select className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <option>Default</option>
              <option>Dark</option>
              <option>Satellite</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
  