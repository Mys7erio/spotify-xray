const FACT_SLIDESHOW_INTERVAL = 8000; // 8 seconds

let ACCESS_TOKEN = "BQARwXTDwIU7X943eiX_4AyhINzYOa4CHAkZAl_fkQT9VIrLp-qvxJZVF78lml9HyPU-dh0u_Duq8LRYjYK_1LTDW5hwHyH04f8d29oH7vIBmEu4MsDl2427efJrUbQ_CCj49EZPlFeBDD7fH9U74f3W8icehnpoiaMGYPRvZSYwqploFUcQdhzc2tauYqnYH6h--HZlmvKIUM3-YNRUMGyexahb7ylWXTBoWLAqJWrHnkzPk-KpuRk";

window.onload = function() {
    const source = new EventSource("http://127.0.0.1:5173/xray?access_token=" + ACCESS_TOKEN);

    let factIntervalId = null;
    let previousFacts = null; // Track the facts from the previous message

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Update song title, artist, album art, and artist's intent
        document.querySelector("#songTitle").textContent = data.item.name;
        document.querySelector("#albumArt").src = data.item.album.images[0].url;
        document.querySelector("#songArtists").textContent = data.item.artists.map(artist => artist.name).join(", ");
        document.querySelector("#artistIntent").textContent = data.meaning;

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
        console.error("EventSource failed:", e);
    });

    function factCarousel(facts) {
        const factElement = document.querySelector("#songFact");
        
        if (!facts || facts.length === 0) {
            factElement.textContent = "No interesting facts available for this song.";
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
