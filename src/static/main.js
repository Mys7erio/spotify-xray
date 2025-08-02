const FACT_SLIDESHOW_INTERVAL = 8000; // 8 seconds


window.onload = function() {
    // Check if the browser has a SESSIONID
    const sessionId = document.cookie.split('; ').find(row => row.startsWith('SESSIONID='));
    if (!sessionId) {
        window.location.href = "/authorize";
    }

    // Connect to the xray endpoint (access_token will be sent via cookie)
    const source = new EventSource("/xray");

    let factIntervalId = null;
    let previousFacts = null; // Track the facts from the previous message

    source.onmessage = (event) => {
        // console.log("SongInfo:", event.data);
        
        const data = JSON.parse(event.data);
        if (data.is_playing) {
            console.log("Currently playing:", data.item.name);
            // Update song title, artist, album art, and artist's intent
            document.querySelector("#songTitle").textContent = data.item.name;
            document.querySelector("#albumArt").src = data.item.album.images[0].url;
            document.querySelector("#songArtists").textContent = data.item.artists.map(artist => artist.name).join(", ");
            document.querySelector("#artistIntent").textContent = data.meaning;
        }
        const currentFacts = data.facts;

        // Only restart the carousel if the facts have changed (e.g., new song)
        const factsChanged = JSON.stringify(currentFacts) !== JSON.stringify(previousFacts);
        if (factsChanged) {
            if (factIntervalId) {
                clearInterval(factIntervalId);
            }
            factIntervalId = factCarousel(currentFacts);
            previousFacts = currentFacts; // Update the tracked facts
        }
    };

    source.addEventListener("error", (e) => {
        console.log("Error from EventSource:", Object.keys(e));
    });

    function factCarousel(facts) {
        const factElement = document.querySelector("#songFact");
        
        if (!facts || facts.length === 0) {
            // factElement.textContent = "No interesting facts available for this song.";
            return null;
        }

        let currentFactIndex = 0;
        
        // Display the first fact immediately
        factElement.textContent = facts[currentFactIndex];

        // Start the interval to cycle through the rest of the facts
        const intervalId = setInterval(() => {
            currentFactIndex = (currentFactIndex + 1) % facts.length;
            factElement.textContent = facts[currentFactIndex];
        }, FACT_SLIDESHOW_INTERVAL); // Change fact every 8 seconds

        return intervalId;
    }
};
