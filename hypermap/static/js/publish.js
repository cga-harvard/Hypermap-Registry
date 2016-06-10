
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

$('#publish-resource').click(function(event) {

    var data = null;

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
            console.log(xml);
        }
    });
});
