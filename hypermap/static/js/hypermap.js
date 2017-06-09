
function gen_harvest_request(resourcetype, source) {
    var xml = '<Harvest service="CSW" version="2.0.2" xmlns="http://www.opengis.net/cat/csw/2.0.2">';
    xml += '<Source>' + source + '</Source>';
    xml += '<ResourceType>' + resourcetype + '</ResourceType>';
    xml += '</Harvest>';

    return xml;
}

function gen_transaction_insert_request(csw_xml) {
    var xml = '<Transaction service="CSW" version="2.0.2" xmlns="http://www.opengis.net/cat/csw/2.0.2">';
    xml += '<Insert>';
    xml += csw_xml;
    xml += '</Insert>';
    xml += '</Transaction>';

    return xml;
}

function focus_page() {
    // autofocus on page inits

    var focus_fields = [
        'input#id_old_password',
        'input#id_username',
        'input[name=q]'
    ];

    for (var i = 0; i < focus_fields.length; i++) {
        if ($(focus_fields[i]).length) {
            $(focus_fields[i]).focus();
        }
    }
}

$('#publish-resource').click(function(event) {

    var data = null;

    var $publish_button = $(this);
    $publish_button.button('loading');

    var publishtype = $('#csw-publishtype').val();
    var resourcetype = $('#csw-resourcetype').val();
    var source = $('#csw-source').val();
    var csw_url = $('#csw-url').val();
    var csw_xml = $('#csw-xml').val();

    if (publishtype === 'Layer') {
        data = gen_transaction_insert_request(csw_xml);
    } else {
        data = gen_harvest_request(resourcetype, source);
    }

    console.log(data);

    $.ajax({
        type: 'post',
        crossDomain: true,
        url: csw_url,
        data: data,
        dataType: 'text',
        success: function(xml) {
            var result_text = null;

            $("#csw-publish-result").removeClass('alert-success');
            $("#csw-publish-result").removeClass('alert-danger');

            $xml = $($.parseXML(xml));
            var exception = $xml.find('ows\\:ExceptionText').text();
            if (exception) {
                $("#csw-publish-result").addClass('alert-danger');
                result_text = 'CSW-T Error: ' + exception;
            } else {
                $("#csw-publish-result").addClass('alert-success');
                var inserted = $xml.find('csw\\:totalInserted').text();
                var updated = $xml.find('csw\\:totalUpdated').text();
                var deleted = $xml.find('csw\\:totalDeleted').text();
                result_text = 'inserted: ' + inserted + " " + 'updated: ' + updated + " " + 'deleted: ' + deleted;
            }
            $("#csw-publish-result").removeClass('hidden');
            $("#csw-publish-result-text").html(result_text);
            $publish_button.button('reset');
            console.log(xml);
        }
    });
});

// page init
$(function() {
    focus_page();
});
