document.addEventListener('DOMContentLoaded', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      var currentTab = tabs[0];
      var url = new URL(currentTab.url);
      var domain = url.hostname;

      fetch(`http://ip-api.com/json/${domain}`)
        .then(response => response.json())
        .then(data => {
          var locationDiv = document.getElementById('location');
          var mapLink = document.getElementById('map-link');
          if (data.status === 'success') {
            locationDiv.textContent = `Country: ${data.country}
  Region: ${data.regionName}
  City: ${data.city}
  ISP: ${data.isp}`;

            // Create Google Maps link
            var mapsUrl = `https://www.google.com/maps?q=${data.lat},${data.lon}`;
            mapLink.href = mapsUrl;
            mapLink.style.display = 'inline-block';
          } else {
            locationDiv.textContent = 'Unable to find server location.';
            mapLink.style.display = 'none';
          }
        })
        .catch(error => {
          console.error('Error:', error);
          document.getElementById('location').textContent = 'Error occurred while fetching location.';
          document.getElementById('map-link').style.display = 'none';
        });
    });
  });