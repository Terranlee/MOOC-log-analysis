// 绿色link表示变得不活跃的用户
// 红色link表示新变活跃的用户
// Active类别的Node以蓝色表示
// 其他均为默认颜色
var color_green = "#00EE00";
var color_red = "#FF0000";
var color_blue = "#0000EE";
var default_node_color = "#E8E2FF";

// 匹配节点类型的正则表达式
var active_reg = new RegExp("_Active$");
var new_reg = new RegExp("_New$");
var never_new_reg = new RegExp("_NNew$");
var nactive_reg = new RegExp("_NActive$");
var never_nactive_reg = new RegExp("_NNactive$");

// 是否缩小new和nactive的stream的宽度
// 缩小之后，统一active节点两侧的new和nactive的最大宽度
// 目前设定为active到active的最大值
var if_shrink = 1;
var shrink_max = 0;

// 是否需要bubble
// 显示的是每个stream的真实值，但是反而可能产生误导
// 所以默认不适用bubble
var if_need_bubble = 0;

var all_node_name;

function list_to_string(list) {
    return list.join(",");
}

function paint_sankey(datapath){

    var sankey = new Sankey();

    function sankey_add_stack(nodes) {
        for(var i=0; i<nodes.length; i++){
            sankey.stack(i, nodes[i]);
        }
    }

    function sankey_add_links(links) {
        sankey.setData(links);
    }

    function sankey_set_color(names) {

        var new_color_dict = Array();
        var nactive_color_dict = Array();
        for(var key in names){
            if(new_reg.test(key)){
                new_color_dict[key] = color_red;
            }
            else if(nactive_reg.test(key)){
                nactive_color_dict.push(key);
            }
        }
        sankey.setColors(new_color_dict);
        sankey.nudge_colours_callback = function(){
            for(var i=0; i<nactive_color_dict.length; i++)
                this.recolour(this.boxes[nactive_color_dict[i]].left_lines, color_green);
        }

        // set the color for bubble
        if(if_need_bubble){
            sankey.bubbleColor = "#F00"
            sankey.bubbleLabelColor = "#fff"
            sankey.negativeBubbleColor = "#0F0"
            sankey.negativeBubbleLabelColor = "#000"
        }
    }

    function sankey_set_bubble(links) {
        var bubble_array = Array();
        // when dealing with the bubbles, use the true number of people, not the shrinked ones
        for(var i=0; i<links.length; i++){
            // new active user, positive value
            if(new_reg.test(links[i][0])){
                bubble_array.push( [ links[i][0], all_node_name[links[i][0]].length ] );
            }
            // not active user, negative value
            else if(nactive_reg.test(links[i][2])){
                bubble_array.push( [ links[i][2], all_node_name[links[i][2]].length * -1 ] );
            }
        }
        sankey.setBubbles(bubble_array);
    }

    function calc_shrink_max(links) {
        // get the max value from active_node to active_node
        var max_val = links[1][1];
        for(var i=1; i<links.length; i=i+3){
            if(links[i][1] > max_val)
                max_val = links[i][1]
        }
        return max_val;
    }

    function shrink_data(links) {
        shrink_max = calc_shrink_max(links);
        console.log(shrink_max);
        // three link data are related with each other
        for(var i=2; i<links.length-1; i=i+3){
            var minv = Math.min(links[i][1], links[i+1][1]);
            var diff = minv - shrink_max;
            if(diff > 0){
                links[i][1] -= diff;
                links[i+1][1] -= diff;
            }
        }
    }

    $.getJSON(datapath, function(data){
        if(if_shrink)
            shrink_data(data.links);

        all_node_name = data.names;
        
        sankey_add_stack(data.nodes);
        sankey_add_links(data.links);
        if(if_need_bubble)
            sankey_set_bubble(data.links);
        sankey_set_color(data.names);

        sankey.draw();
    });
    /*
    sankey.nudge_colours_callback = function(){
        this.recolour(this.boxes["Bad"].left_lines, "#FF6FCF");
    }
    */
}
