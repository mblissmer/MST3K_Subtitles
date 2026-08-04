let fuse;
let searchData = [];


async function loadSearchIndex() {

    const response = await fetch("search-index.json");

    searchData = await response.json();

    fuse = new Fuse(searchData, {
        keys: [
            "text"
        ],
        threshold: 0.35,
        includeMatches: true
    });

    document.getElementById("searchBox").disabled = false;

    document.getElementById("subtitleCount").textContent =
        new Set(searchData.map(x => x.file)).size;
}


function searchSubtitles() {

    const query =
        document.getElementById("searchBox").value.trim();

    const results =
        document.getElementById("results");


    if (!query) {
        results.innerHTML = "";
        return;
    }


    const matches = fuse.search(query);


    if (matches.length === 0) {

        results.innerHTML =
            "<p>No matches found.</p>";

        return;
    }


    let html = "";

    for (const match of matches.slice(0, 50)) {

        const item = match.item;


        html += `
        <hr>

        <p>
        <b>
        S${String(item.season).padStart(2,"0")}
        E${String(item.episode).padStart(2,"0")}
        - ${item.title}
        </b>
        </p>

        <p>
        <small>${item.time}</small>
        </p>

        <blockquote>
        ${item.text}
        </blockquote>

        <p>
        <a href="${item.file}">
        Download subtitle
        </a>
        </p>
        `;
    }


    results.innerHTML = html;
}


loadSearchIndex();