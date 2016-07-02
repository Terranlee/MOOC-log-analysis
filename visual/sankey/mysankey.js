// 几种可能用到的颜色
var color_green = "#00EE00";
var color_dark_green = "#6B8E23";
var color_red = "#FF0000";
var color_dark_red = "#800000";
var color_blue = "#0000EE";
var default_node_color = "#E8E2FF";

// 绿色link表示变得不活跃的用户，深绿色表示以后再也没有活跃过的用户
// 红色link表示新变活跃的用户，深红色表示以前从没有活跃过的用户
// Active类别的Node以蓝色表示
// 其他均为默认颜色
var color_active = color_blue;
var color_nactive = color_green;
var color_nnactive = color_dark_green;
var color_new = color_red;
var color_nnew = color_dark_red;

// 匹配节点类型的正则表达式
var active_reg = new RegExp("_Active$");
var new_reg = new RegExp("_New$");
var never_new_reg = new RegExp("_NNew$");
var nactive_reg = new RegExp("_NActive$");
var never_nactive_reg = new RegExp("_NNactive$");

// 共计有5种类型的link
// 其中active到active的link在第2个位置上
var start_pos = 2;
var num_of_link = 5;

// 是否需要bubble
// 显示的是每个stream的真实值，但是反而可能产生误导
// 所以默认不适用bubble
var if_need_bubble = 0;

// 所有node或者link对应的人名
var all_node_name;

// 是否缩小new和nactive的stream的宽度
var if_shrink = 0;

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
        // some temp dictionary to save the color mapping
        var new_color_dict = Array();
        var nactive_color_dict = Array();
        var never_nactive_color_dict = Array();
        for(var key in names){
            // for new or never_new, the link is on the right side, so set directly
            if(new_reg.test(key)){
                new_color_dict[key] = color_new;
            }
            else if(never_new_reg.test(key)){
                new_color_dict[key] = color_nnew;
            }
            // for nactive and never_nactive, the link is on the left side
            // so use nudge_callback to set the color
            else if(nactive_reg.test(key)){
                nactive_color_dict.push(key);
            }
            else if(never_nactive_reg.test(key)){
                never_nactive_color_dict.push(key);
            }
        }
        // set the right link of a node
        sankey.setColors(new_color_dict);
        // set the left link of a node
        sankey.nudge_colours_callback = function(){
            for(var i=0; i<nactive_color_dict.length; i++)
                this.recolour(this.boxes[nactive_color_dict[i]].left_lines, color_nactive);
            for(var i=0; i<never_nactive_color_dict.length; i++)
                this.recolour(this.boxes[never_nactive_color_dict[i]].left_lines, color_nnactive);
        }

        // set the color for bubble, only if needed
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
        var max_val = links[start_pos][1];
        for(var i=start_pos; i<links.length; i=i+num_of_link){
            if(links[i][1] > max_val)
                max_val = links[i][1]
        }
        return max_val;
    }

    function shrink_data_maxval(links) {
        // shrink the data using the max value of active to active
        var shrink_max = calc_shrink_max(links) * if_shrink;
        //console.log(shrink_max);
        // three link data are related with each other
        for(var i=start_pos; i<links.length-num_of_link; i=i+num_of_link){
            // calculate the sum value of new and nactive
            var sum_new = links[i+1][1] + links[i+2][1];
            var sum_nactive = links[i+3][1] + links[i+4][1]
            var minv = Math.min(sum_new, sum_nactive);
            // diff means the total value need to be shrinked
            var diff = minv - shrink_max;
            if(diff > 0){
                links[i+1][1] -= parseInt(diff * links[i+1][1] / sum_new);
                links[i+2][1] -= parseInt(diff * links[i+2][1] / sum_new);
                links[i+3][1] -= parseInt(diff * links[i+3][1] / sum_nactive);
                links[i+4][1] -= parseInt(diff * links[i+4][1] / sum_nactive);
            }
        }
    }

    $.getJSON(datapath, function(data){
        if(if_shrink)
            shrink_data_maxval(data.links);
        //console.log(if_shrink);
        all_node_name = data.names;
        
        sankey_add_stack(data.nodes);
        sankey_add_links(data.links);
        if(if_need_bubble)		// set bubble if needed
            sankey_set_bubble(data.links);
        sankey_set_color(data.names);

        sankey.draw();
    });
}
