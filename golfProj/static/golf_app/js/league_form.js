$(document).ready(function() {
  console.log('ready');
})

$(function() {
  $('#email_cnt').change(function () {
    var orig_forms = $('#id_form-TOTAL_FORMS').val()
    new_cnt = $('#email_cnt').val()
    additional_forms = (new_cnt) - orig_forms
    //cloneMore(total_forms, additional_forms)//
    //console.log($('#id_form-TOTAL_FORMS').val());
    i = parseInt(orig_forms)
    //subtract 1 as form index starts at 0 so want one less than user request
    for (var i; i <= new_cnt - 1; i++) {
      //console.log(i, i + parseInt(additional_forms), additional_forms);
      $('#form_set').append($('#empty_form').html().replace(/__prefix__/g, i));
    }
    $('#id_form-TOTAL_FORMS').val(parseInt(new_cnt));
    //console.log($('#id_form-TOTAL_FORMS').val());
  });
});
//
//function cloneMore(orig_num, additional_forms) {
//  console.log('in clone', orig_num, additional_forms);
//  var form_idx = orig_num
//  $('#form_set').append($('#empty_form').html().replace(/__prefix__/g, orig_num));
//       $('#id_form-TOTAL_FORMS').val(parseInt(orig_num) + 1);

//}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}


function send_email(league, invite) {
  console.log(invite);
  var csrf_token =$("[name=csrfmiddlewaretoken]").val();
  var invite_list = []
  if (invite == 'all') {
    for (var j = 0; j < $('#email_cnt').val(); j++) {
    invite_list.push($('#id_form-' + j + '-id').val(), $('#id_form-' + j + '-email_address').val())
    }}
  else {
        console.log('else', $("#invite_form-" + invite).children().val());
        invite_list.push(invite, $("#invite_form-" + invite).children().val())
  }
  var list = JSON.stringify(invite_list)
  console.log(invite_list);
  $.ajax({
    beforeSend: function(xhr, settings) {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrf_token);
        }
    },
    type: "POST",
    url: "/golf_app/ajax/resend_invites/",
    dataType: 'json',
    data: {'league': league,
           'invite_list': list
         },
    //context: document.body
    success: function(data) {
      console.log(data);
      alert('emails sent')
    },
    failure: function() {
      console.log('fail');
      console.log(json);
    }
  })

}
