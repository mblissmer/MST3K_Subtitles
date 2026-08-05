let fuse;
let searchData = [];


async function loadSearchIndex() {
    const response = await fetch("search-index.json");
    searchData = await response.json();
    fuse = new Fuse(searchData, {
        keys: ["text"],
        threshold: 0.35,
        includeMatches: true
    });
    document.getElementById("searchBox").disabled = false;
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
    const grouped = new Map();
    for (const result of fuse.search(query)) {   
        const item = result.item;
        const key = item.file;
        if (!grouped.has(key)) {
            grouped.set(key, {
                season: item.season,
                episode: item.episode,
                title: item.title,
                file: item.file,
                hits: []
            });
        }
        grouped.get(key).hits.push({
            time: item.time,
            text: item.text
        });
    }


    let html = "";
    for (const episode of grouped.values()) {
        html += `
            <hr>
            <h3>
                S${String(episode.season).padStart(2,"0")}
                E${String(episode.episode).padStart(2,"0")}
                - ${episode.title}
            </h3>
        `;
        for (const hit of episode.hits) {
            html += `
                <div class="hit">
                    <b>${hit.time}</b> &quot;...${hit.text}...&quot;
                </div>
            `;
        }
        html += `
            <p>
                <a href="${episode.file}">
                    Download subtitle
                </a>
            </p>
        `;
    }
    results.innerHTML = html;
}

loadSearchIndex();
