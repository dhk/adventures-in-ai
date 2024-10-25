import React, { useState } from 'react';

function App() {
  const [message, setMessage] = useState('');
  const [datetime, setDatetime] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    const data = {
      message: message,
      datetime: datetime,
    };

    try {
      const response = await fetch('http://localhost:5000/schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      alert(result.status);
    } catch (error) {
      console.error('Error details:', error);
      alert('Failed to schedule post. Check the console for more details.');
    }
  };

  return (
    <div className="App">
      <h1>Schedule Facebook Post</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Message:
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
          />
        </label>
        <br />
        <label>
          Schedule Time:
          <input
            type="datetime-local"
            value={datetime}
            onChange={(e) => setDatetime(e.target.value)}
            required
          />
        </label>
        <br />
        <button type="submit">Schedule Post</button>
      </form>
    </div>
  );
}

export default App;