jQuery(document).ready(function(e){
jQuery('div#ldap_links a').click(function(e){
    jQuery.get('./ajax/'+this.href.replace('#',''),
        function(data){
            jQuery('div#ldap_contents').empty();
            jQuery('div#ldap_contents').prepend(data);
        });                    
    e.preventDefault();
    e.stopPropagation();
});});
