ACCESS_TOKEN="BQBH98uXbUqAQQBnDf450K-XlUF5Uh5Vfqq-lAb2zIBq7RfyA1q8aZ5QlCEEEyNyyE5zeQ_RRuj_Qgl89cDPLcQYQSe25a5DqSLte6O5BB8NUqyVnmC4a_BRLDtxDiLZUdfL-T_1OSR9Esn3s5-_KvKvVlSkO63aSd76IxMq4aFL4cTWFvGU1exybpnCMMxL5FEvNgoOM2Iu_FGOh-sXplUQ_K6k3qEQEcvtapGzgQip_oCFdL-4hjQ"



window.onload = function() {
    const source = new EventSource("http://127.0.0.1:5173/xray?access_token=" + ACCESS_TOKEN);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // console.log(data);

        let newTitle = data["item"]["name"]
        let albumArt = data["item"]["album"]["images"][0]["url"]
        let artistIntent = data["meaning"]
        let interestingFacts = data["facts"]
        // console.log(artistIntent, interestingFacts);

        document.querySelector("#songTitle").textContent = newTitle;
        document.querySelector("#albumArt").src = albumArt;
        document.querySelector("#songArtists").textContent = data["item"]["artists"].map(artist => artist.name).join(", ");
        document.querySelector("#artistIntent").textContent = artistIntent;
        // document.querySelector(".interesting-facts-section").appendChild(document.createTextNode(interestingFacts[1])); 
        factCarousel(interestingFacts);

        function factCarousel(facts) {
            let noFacts = facts.length;
            let currentFactIndex = 0;

            // while (true) {
            //     currentFactIndex = (currentFactIndex + 1) % noFacts;
            //     let factElement = document.querySelector("#songFact");
            //     factElement.textContent = facts[currentFactIndex];
            //     console.log(`Fact: ${facts[currentFactIndex]}`);
            //     setTimeout(() => {}, 5000); // Change fact every 5 seconds
            // }

            setInterval(() => {
                currentFactIndex = (currentFactIndex + 1) % noFacts;
                let factElement = document.querySelector("#songFact");
                factElement.textContent = facts[currentFactIndex];
            }, 8000); // Change fact every 8 seconds
        }
    };

    source.addEventListener("error", (e) => {
        console.error(e);
    });
}