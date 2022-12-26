var zones = {}

function setZones() {
    $("#nac-zone").empty()
    var selected = $("#nac-center option:selected").text();
    zones[$("#nac-center option:selected").text()]['zones'].map((e) => $('#nac-zone').append(new Option(e['name'], e['id'])))
}

$('#nac-center').change(setZones);

fetch("https://avymail.fly.dev/zones")
    .then((response) => response.json())
    .then((data) => {
        $("#nac-center").empty();
        zones = data;
        Object.entries(data).map((e) => $("#nac-center").append(new Option(e[0], e[1]['center_id'])));
        setZones();
    })

function subscribe() {
    var center_id = $("#nac-center option:selected").val()
    var zone_id = $("#nac-zone option:selected").val()
    var email = $("#email").val()
    var body = {
        email: email,
        center_id: center_id,
        zone_id: zone_id
    }
    console.log(JSON.stringify(body))
    fetch("https://avymail.fly.dev/add", {
        method: 'POST',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify(body)
    })
        .then((res) => {
            if (res.ok) {
                return res.json()
            }
            return Promise.reject(res)
        })
        .then((data) => {
            $("#postsub-message").text("Success.")
        })
        .catch((r) => {
            console.log(r)
            r.json().then((json) => {
                console.log(json);
                $("#postsub-message").text("Errors: ")
                if (json['detail'].constructor === Array) {
                    $("#postsub-message").append(
                        json['detail'].map((e) => e['msg']).join(', ')
                    )
                }
                else {
                    $("#postsub-message").append(json['detail'])
                }

            })
        })
}

$("#subscribe").click(subscribe)