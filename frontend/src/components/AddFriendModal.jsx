import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './AddFriendModal.css';

function AddFriendModal({ onClose }) {
  const [friendUsername, setFriendUsername] = useState('');
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  const { token } = useAuth();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');
    setIsError(false);

    if (!token) {
      setMessage('You must be logged in to add friends.');
      setIsError(true);
      return;
    }

    try {
      const response = await fetch('/friends', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ friend_username: friendUsername }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(`${data.username} (ID: ${data.id}) has been added as a friend!`);
        setFriendUsername('');
        // Optionally, close the modal after a short delay
        setTimeout(onClose, 2000);
      } else {
        const errorData = await response.json();
        setMessage(errorData.detail || 'Failed to add friend.');
        setIsError(true);
      }
    } catch (err) {
      setMessage('An error occurred while adding friend.');
      setIsError(true);
    }
  };

  return (
    <div className="add-friend-modal-overlay">
      <div className="add-friend-modal-content">
        <h2>친구 추가</h2>
        <form onSubmit={handleSubmit}>
          <div className="add-friend-input-group">
            <label htmlFor="friendUsername">친구의 사용자 이름</label>
            <input
              type="text"
              id="friendUsername"
              value={friendUsername}
              onChange={(e) => setFriendUsername(e.target.value)}
              required
            />
          </div>
          {message && (
            <p className={isError ? 'add-friend-error-message' : 'add-friend-success-message'}>
              {message}
            </p>
          )}
          <div className="add-friend-actions">
            <button type="submit" className="add-friend-submit-button">추가</button>
            <button type="button" className="add-friend-cancel-button" onClick={onClose}>취소</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddFriendModal;
