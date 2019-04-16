$(document).ready(function() {
  console.log('first step');

  $.ajax({
    type: "GET",
    url: "/golf_app/scores/",
    dataType: 'json',
    //context: document.body
    success: function (json) {
      console.log('connected');
      // var i;
      // for (i = 0; i < json.length; ++i) {
      //     $('#' + json[i]).attr('checked', 'checked');
      //   }
    },
    failure: function(json) {
      console.log('fail');
      console.log(json);
    }
  })

})
