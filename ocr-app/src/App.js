/*import React, { useState } from 'react';
import './index.css';
export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setResult('');
    setLoading(true);

    const formData = new FormData();
    formData.append('image', file);

    try {
      const res = await fetch('/api/ocr', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.status === 'success') {
        setResult(data.full_text || 'No text detected.');
      } else {
        setResult('Error: ' + (data.message || 'Unknown error'));
      }
    } catch {
      setResult('Error connecting to OCR service.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 text-gray-800 flex flex-col items-center p-4">
      <header className="text-center my-8">
        <h1 className="text-4xl font-bold text-blue-700">OCR Service</h1>
        <p className="text-gray-600 mt-2">Extract text from images quickly and accurately</p>
      </header>

      <main className="w-full max-w-xl bg-white rounded-2xl shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-gray-700 font-medium">Upload Image</span>
            <input
              type="file"
              accept="image/*"
              required
              onChange={e => setFile(e.target.files[0])}
              className="mt-2 w-full border border-gray-300 rounded-md p-2"
            />
          </label>
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition"
          >
            {loading ? 'Processing...' : 'Extract Text'}
          </button>
        </form>

        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-2">OCR Results</h2>
          <div className="whitespace-pre-wrap p-4 bg-gray-50 border rounded-md min-h-[100px]">
            {loading ? 'Processing...' : result}
          </div>
        </div>
      </main>

      <footer className="mt-12 text-sm text-gray-500">
        &copy; 2025 OCR Service. All rights reserved.
      </footer>
    </div>
  );
}
*/

import './App.css';
import './index.css';

import React, { useState } from 'react';

export default function App() {
  const [file, setFile] = useState(null);
  const [output, setOutput] = useState('Output will appear here.');
  const [loading, setLoading] = useState(false);
  const [timeTaken, setTimeTaken] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setOutput(''); // Clear output on new upload
    setTimeTaken(null);
  };

  const handleProcess = async () => {
    if (!file) {
      alert('Please upload a file first!');
      return;
    }
    setLoading(true);
    setOutput('Processing...');
    setTimeTaken(null);

    const formData = new FormData();
    formData.append('image', file);

    const startTime = performance.now();

    try {
      const res = await fetch('http://localhost:5000/api/ocr', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();

      const endTime = performance.now();
      setTimeTaken(((endTime - startTime) / 1000).toFixed(2)); // seconds with 2 decimals

      // Adjust according to your OCRService output structure
      if (data.status === 'error') {
        setOutput(`Error: ${data.message}`);
      } else if (data.text) {
        setOutput(data.text);
      } else {
        setOutput(JSON.stringify(data, null, 2));
      }
    } catch (err) {
      setOutput('Error: ' + err.message);
      setTimeTaken(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 flex flex-col">
      <header className="bg-blue-600 text-white p-4 text-center text-2xl font-bold">
        Street OCR Project
      </header>

      <main className="flex flex-1">
        <section className="w-1/2 p-6 border-r border-gray-300">
          <h2 className="text-xl mb-4 font-semibold">Upload Image</h2>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="mb-4 block w-full"
          />
          {file && (
            <img
              src={URL.createObjectURL(file)}
              alt="preview"
              className="w-full max-h-96 object-contain border rounded"
            />
          )}
          <button
            onClick={handleProcess}
            disabled={loading}
            className={`mt-4 px-4 py-2 rounded text-white ${
              loading ? 'bg-gray-500 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {loading ? 'Processing...' : 'Run OCR'}
          </button>
        </section>

        <section className="w-1/2 p-6 flex flex-col">
          <h2 className="text-xl mb-4 font-semibold">OCR Output</h2>
          <div className="bg-gray-200 p-4 rounded min-h-[300px] whitespace-pre-wrap overflow-auto flex-1">
            {output}
          </div>
          {timeTaken && (
            <p className="mt-2 text-gray-700 font-medium">
              Processing time: {timeTaken} seconds
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
