/**
 * Tailwind CSS Test Page
 * 
 * Debug page to verify Tailwind is working correctly
 */
export default function TailwindTest() {
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="text-4xl font-bold text-blue-600 mb-8">
        Tailwind CSS Test Page
      </h1>
      
      {/* Test 1: Colors */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">1. Colors Test</h2>
        <div className="flex gap-4">
          <div className="w-16 h-16 bg-brand-primary! rounded"></div>
          <div className="w-16 h-16 bg-green-500 rounded"></div>
          <div className="w-16 h-16 bg-blue-500 rounded"></div>
          <div className="w-16 h-16 bg-yellow-500 rounded"></div>
          <div className="w-16 h-16 bg-purple-500 rounded"></div>
          <div className="w-16 h-16 bg-black rounded"></div>
        </div>
      </section>

      {/* Test 2: Typography */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">2. Typography Test</h2>
        <p className="text-xs text-gray-600">Extra Small Text (text-xs)</p>
        <p className="text-sm text-gray-600">Small Text (text-sm)</p>
        <p className="text-base text-gray-700">Base Text (text-base)</p>
        <p className="text-lg text-gray-800">Large Text (text-lg)</p>
        <p className="text-xl font-bold text-gray-900">Extra Large Bold (text-xl)</p>
      </section>

      {/* Test 3: Spacing & Layout */}
      <section className="mb-8 p-4">
        <h2 className="text-2xl font-semibold mb-4">3. Grid & Spacing Test</h2>
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-blue-200 p-4 rounded">Col 1</div>
          <div className="bg-blue-300 p-4 rounded">Col 2</div>
          <div className="bg-blue-400 p-4 rounded text-white">Col 3</div>
          <div className="bg-blue-500 p-4 rounded text-white">Col 4</div>
        </div>
      </section>

      {/* Test 4: Flexbox */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">4. Flexbox Test</h2>
        <div className="flex items-center justify-between bg-gray-200 p-4 rounded">
          <span className="bg-green-500 text-white px-4 py-2 rounded">Left</span>
          <span className="bg-yellow-500 text-black px-4 py-2 rounded">Center</span>
          <span className="bg-red-500 text-white px-4 py-2 rounded">Right</span>
        </div>
      </section>

      {/* Test 5: Shadows & Borders */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">5. Shadows & Borders Test</h2>
        <div className="flex gap-4">
          <div className="w-32 h-32 bg-white shadow rounded p-4">shadow</div>
          <div className="w-32 h-32 bg-white shadow-md rounded p-4">shadow-md</div>
          <div className="w-32 h-32 bg-white shadow-lg rounded p-4">shadow-lg</div>
          <div className="w-32 h-32 bg-white shadow-xl rounded-xl p-4">shadow-xl</div>
          <div className="w-32 h-32 bg-white shadow-2xl rounded-2xl p-4">shadow-2xl</div>
        </div>
      </section>

      {/* Test 6: Hover States */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">6. Hover States Test</h2>
        <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 hover:scale-105 transition-all">
          Hover Me (should change color & scale)
        </button>
      </section>

      {/* Debug Info */}
      <section className="mt-12 p-4 bg-yellow-100 border border-yellow-400 rounded">
        <h2 className="text-xl font-bold text-yellow-800 mb-2">Debug Info</h2>
        <p className="text-yellow-700">
          If you see styled boxes above with colors, shadows, and proper spacing, 
          Tailwind CSS is working correctly!
        </p>
        <p className="text-yellow-700 mt-2">
          If everything looks plain with no styling, Tailwind is NOT loading.
        </p>
      </section>
    </div>
  );
}
