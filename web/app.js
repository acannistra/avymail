var zones = {};

function setZones() {
  $("#nac-zone").empty();
  var selected = $("#nac-center option:selected").text();
  zones[$("#nac-center option:selected").text()]["zones"].map((e) =>
    $("#nac-zone").append(new Option(e["name"], e["id"]))
  );
}

$("#nac-center").change(setZones);

fetch("https://avymail.fly.dev/zones")
  .then((response) => response.json())
  .then((data) => {
    $("#nac-center").empty();
    zones = data;
    Object.entries(data).map((e) =>
      $("#nac-center").append(new Option(e[0], e[1]["center_id"]))
    );
    setZones();
  });

function subscribe() {
  var center_id = $("#nac-center option:selected").val();
  var zone_id = $("#nac-zone option:selected").val();
  var email = $("#email").val();
  var body = {
    email: email,
    center_id: center_id,
    zone_id: zone_id,
  };
  fetch("https://avymail.fly.dev/add", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  })
    .then((res) => {
      if (res.ok) {
        return res.json();
      }
      return Promise.reject(res);
    })
    .then((data) => {
      $("#postsub-message").text(
        "Success. You'll receive your first e-mail within the next 30 minutes with today's forecast."
      );
    })
    .catch((r) => {
      r.json().then((json) => {
        $("#postsub-message").text("Errors: ");
        if (json["detail"].constructor === Array) {
          $("#postsub-message").append(
            json["detail"].map((e) => e["msg"]).join(", ")
          );
        } else {
          $("#postsub-message").append(json["detail"]);
        }
      });
    });
}

function lookupZoneName(center_id, zone_id) {
  for (const [center_name, center_val] of Object.entries(zones)) {
    if (center_val["center_id"] == center_id) {
      for (const zone of center_val["zones"]) {
        if (zone["id"] == zone_id) {
          return zone["name"] + " " + "(" + center_name + ")";
        }
      }
    }
  }
}

function lookupEmail() {
  var email = $("#email-lookup").val();
  $("#subs").empty();
  fetch(
    "https://avymail.fly.dev/subs?" +
      new URLSearchParams({
        email: email,
      })
  )
    .then((res) => {
      if (res.ok) {
        return res.json();
      }
      return Promise.reject(res);
    })
    .then((data) => {
      if (data.length == 0) {
        $("#subs").text("No subscriptions found.");
      }
      $("#subs").append(
        data.map((s) => {
          var unsub_url =
            "https://avymail.fly.dev/remove?" +
            new URLSearchParams({
              email: email,
              center_id: s["center_id"],
              zone_id: s["zone_id"],
            });
          return $("<tr>").append([
            $("<td>").text(lookupZoneName(s["center_id"], s["zone_id"])),
            $('<td style="text-align: right">').append(
              '<a href="' + unsub_url + '">Unsubscribe</a>'
            ),
          ]);
        })
      );
    });
}

$("#start-lookup").click(lookupEmail);
$("#subscribe").click(subscribe);
