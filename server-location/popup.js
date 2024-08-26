// popup.js
document.addEventListener('DOMContentLoaded', function() {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    var currentTab = tabs[0];
    var url = new URL(currentTab.url);
    var domain = url.hostname;

    fetch(`http://ip-api.com/json/${domain}`)
      .then(response => response.json())
      .then(data => {
        var locationDiv = document.getElementById('location');
        if (data.status === 'success') {
          locationDiv.innerHTML = `
            Country: ${data.country}<br>
            Region: ${data.regionName}<br>
            City: ${data.city}<br>
            ISP: ${data.isp}
          `;
        } else {
          locationDiv.textContent = 'Unable to find server location.';
        }
      })
      .catch(error => {
        console.error('Error:', error);
        document.getElementById('location').textContent = 'Error occurred while fetching location.';
      });
  });
});
