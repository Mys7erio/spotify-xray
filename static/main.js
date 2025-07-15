let ACCESS_TOKEN = "BQARwXTDwIU7X943eiX_4AyhINzYOa4CHAkZAl_fkQT9VIrLp-qvxJZVF78lml9HyPU-dh0u_Duq8LRYjYK_1LTDW5hwHyH04f8d29oH7vIBmEu4MsDl2427efJrUbQ_CCj49EZPlFeBDD7fH9U74f3W8icehnpoiaMGYPRvZSYwqploFUcQdhzc2tauYqnYH6h--HZlmvKIUM3-YNRUMGyexahb7ylWXTBoWLAqJWrHnkzPk-KpuRk"


window.onload = function() {
    const source = new EventSource("http://127.0.0.1:5173/xray?access_token=" + ACCESS_TOKEN);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);

        let newTitle = data["item"]["name"]
        let albumArt = data["item"]["album"]["images"][0]["url"]
        let artistIntent = data["meaning"]
        let interestingFacts = data["facts"]

        document.querySelector("#songTitle").textContent = newTitle;
        document.querySelector("#albumArt").src = albumArt;
        document.querySelector("#songArtists").textContent = data["item"]["artists"].map(artist => artist.name).join(", ");
        document.querySelector("#artistIntent").textContent = artistIntent;
        factCarousel(interestingFacts);

        function factCarousel(facts) {
            let noFacts = facts.length;
            let currentFactIndex = 0;

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