// 颜色
// color_function决定颜色如何生成
// color_function = 0，表示采用插值方法生成颜色
// color_function = 1，表示采用随机方法生成颜色
var color_function = 1;
var red_color = d3.rgb(255,0,0);    //红色
var green_color = d3.rgb(0,255,0);    //绿色
var compute = d3.interpolate(red_color, green_color);
var color_linear = d3.scale.linear().range([0,1]);
var random_color = d3.scale.category20();

// streamgraph的高度
// 所有stream叠加在一起的时候，高度为total_height
// 每一个stream分别显示的时候，总高度为single_height_sum
// blank是在svg顶端空出来的，不要太挤
// lable_location指的是single_stream绘制的时候，每个label的定位，在[0,1]区间中
var total_height = 400;
var single_height_sum = 2000;
var blank_total = 10;
var blank_single = 50;
var label_location = 0.4;

// svg大小设定
var margin = {top: 20, right: 40, bottom: 30, left: 30};
var width = document.body.clientWidth - margin.left - margin.right;

// 时间格式化
var format = d3.time.format("%y-%m-%d");

// mouseover动画效果的渐变时间
var mouseover_duration = 200;

// allstream显示时，通过threshold消除掉一部分数据，否则stack图上太多的stream叠加显得太乱
// which_threshold选择通过哪种方式进行数据消除，如果为0，则表示通过百分比的阈值进行消除，如果为1，则表示通过排名消除
var which_threshold = 1;
// 对于某一个stream，如果某个时间点的值小于该stream最大值的percent_threshold倍，则消除
var percent_threshold = 0.1;
// 对于每个时间点上的stream值进行排序，只保留前sort_threshold个
var sort_threshold = 3;

// SVG绘图相关的全局变量

// 可以在这里先设定一个值域，之后再在后面设置定义域
// time.scale用法和scale一样
var x = d3.time.scale()
    .range([0, width]);

// 创建坐标轴
var xAxis = d3.svg.axis()
    .scale(x)   // 坐标轴一定是和一个比例尺绑定在一起的
    .orient("bottom")   // 刻度显示在什么方向，这里是在下面
    .ticks(d3.time.weeks);  // tick表示显示出多少个刻度，这个意思应该是每周显示一个刻度

// stack图相当于是处理一个二维数组，横轴方向有若干列，每一列有是由若干block堆叠而成的
var stack = d3.layout.stack()
    //.offset("silhouette")
    .values(function(d) { return d.values; })   
    // 这句相当于一个设定，之后当我访问values的时候，我访问的是data的values，相当于是数组的第一维
    // d.values，因为之前通过nest进行了转换，第一个维度是key : values的映射，所以values之后就指向数组的第二维了
    .x(function(d) { return d.date; })          
    // 当我访问x的时候，我访问的是data的date，这个是相对于values来说的，相当于是数组的第二维
    .y(function(d) { return d.value; });        
    // y相当于是每一个小block的高度，stack的layout会自动把所有的y叠加起来得到整体的高度的    

// nest将数据转换为层级标识，应该是类似高维数组，有点类似与SQL中的group by
// 输入可能是一个一维数组，每个元素都是某种object，现在想要根据object中的某些属性，将数据转换成为高维数组
// 每一层数据都自动转换成为key : values的形式
var nest = d3.nest()
    .key(function(d) { return d.key; });        
    // d.key是data.csv中的key，也就是课程ID，用这个作为第一层的group by
    // 之后就得到数组的第一个维度了，相同课程ID的那些entry形成第二个维度
    // key函数可以连续调用，就可以生成更高维度的数组了


function chart_allstream(csvpath) {
    // 全局最大值以及只显示某一stream时的局部最大值
    var global_maxval = 0;
    var local_maxval = 0;
    
    // 在allstream中是否展示全部的数据，is_all为1则展示全部数据，否则只展示allstream的部分数据
    // which_one就是选择数据时候的key
    var is_all = 1;
    var which_one;

    var height = total_height - margin.top - margin.bottom;
    
    var datearray = [];

    // tooltip就是左上角显示那个class1,class2的地方
    var tooltip = d3.select("body")
        .append("div")
        .attr("class", "remove")
        .style("position", "absolute")
        .style("z-index", "20")
        .style("visibility", "hidden")
        .style("top", "30px")
        .style("left", "55px");
        
    // d3.scale是创建比例尺，相当于是一个映射关系
    // domain是定义域，range是值域，默认为[0,1]
    // y相当于就是一个函数了，之后调用y(100.0)，返回映射后的值
    var y = d3.scale.linear()
        .range([height - blank_total, 0]);
    
    // 好像是某种圆形插值的算法，给定一个数组，就能生成各种形状
    var area = d3.svg.area()
        .interpolate("cardinal")
        .x(function(d) { return x(d.date); })
        .y0(function(d) { return y(d.y0); })
        .y1(function(d) { return y(d.y0 + d.y); });
            
    // 创建一块svg画布，设定高度，设定宽度
    var svg = d3.select(".chart").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        // g是group的意思，可以将元素进行分组，之后可能比较好管理吧，暂时没看到用处
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    function threshold_percent(data){
        // get the max value of each key
        var key_maxval = Array();
        data.forEach(function(d) {
            if(!key_maxval[d.key])
                key_maxval[d.key] = 0;
            if(d.value > key_maxval[d.key])
                key_maxval[d.key] = d.value;
        });
        // multiply by threshold
        for(var key in key_maxval){
            key_maxval[key] = percent_threshold * key_maxval[key];
        }
    
        // remove some of the data
        data.forEach(function(d) {
            if(d.value < key_maxval[d.key]){
                d.value = 0;
            }
        });
    }    
    
    function threshold_sort(data){
        // reorder the data by date
        var date_maxval_list = Array();
        data.forEach(function(d) {
            if(!date_maxval_list[d.date])
                date_maxval_list[d.date] = [];
            date_maxval_list[d.date].push(d.value);
        });
    
        function numDescSort(a, b){ return b - a;   }
        for(var date in date_maxval_list){
            date_maxval_list[date].sort(numDescSort);
        }
    
        for(var date in date_maxval_list){
            date_maxval_list[date] = date_maxval_list[date][sort_threshold-1];
        }
    
        // remove some of the data
        data.forEach(function(d) {
            if(d.value < date_maxval_list[d.date])
                d.value = 0;
        });
    }
    
    function allstream_preprocess(data, if_threshold){
        // get the global_maxval
        data.forEach(function(d) {
            d.value = +d.value;
            if(d.value > global_maxval){
                global_maxval = d.value;
            }
        });
        local_maxval = global_maxval;        
        if(if_threshold){
            // use threshold to remove some data
            if(which_threshold == 0){
                threshold_percent(data);
            }
            else if(which_threshold == 1){
                threshold_sort(data);
            }
        }
    }
    
    function clear(){
        svg.selectAll(".layer").remove();
        d3.select(".chart").select(".remove").remove();
    }
    
    // generate a permutated array, used by the color function
    function permutation(length){
        var unordered_array = Array();
        for(var i=0; i<length; i++){
            unordered_array.push(i);
        }
        for(var i=0; i<length; i++){
            var iRand = parseInt(length * Math.random());
            var temp = unordered_array[i];
            unordered_array[i] = unordered_array[iRand];
            unordered_array[iRand] = temp;
        }
        return unordered_array;
    }

    function paint(data){
        // 对于每一个data的object进行如下的处理，时间的格式化
        data.forEach(function(d) {
            d.date = format.parse(d.date);
            d.value = +d.value;
        });
        // 按照定义好的nest，将原始的一维data转换为二维data，然后传递给stack
        // 主要就是增加了y和y0，data原始数据中也添加了y0和y这些信息
        // 之后返回的layers是一个分层结构，但是data仍然是一维结构，只是增加了更多的内容，比如y0
        var layers = stack(nest.entries(data));
        // initialize color using linear interpolate
        color_linear.domain([0, layers.length]);
        strokecolor = compute(color_linear(0));

        x.domain(d3.extent(data, function(d) { return d.date; }));
        y.domain([0, d3.max(data, function(d) { return d.y0 + d.y; })]);
        // selectAll选中了一批元素，可能比需要的多，可能比需要的少，甚至可能为0个
        // data是数据，相当于一个array
        // enter函数，返回了数据比元素多的部分。update是数据和元素相同多的部分。exit是数据比元素少的部分

        // 随机颜色生成
        var perm = permutation(layers.length);
        svg.selectAll(".layer")
            .data(layers)
            .enter().append("path")
            .attr("class", "layer")
            .attr("d", function(d) { return area(d.values); })
            .style("fill", function(d, i) { 
                if(color_function == 0){
                    return compute(color_linear(perm[i]));
                }
                else if(color_function == 1){
                    return random_color(i);
                }
                });
            
        // 添加坐标轴的方法
        // 选中svg，增加一个分组g，translate是进行一下平移
        // call函数，参数也是一个函数，功能是把当前的选择集作为参数，传递给xAxis这个函数
        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis);
        svg.selectAll(".layer")
            .attr("opacity", 1)
            // select得到的每一个选择集都可以通过on添加事件监听器
            // 最新一次发生的时间会被保存到d3.event中，可以直接console.log(d3.event)查看
            // function(d, i)仍然是d标识对应的layer，i标识下标
            .on("mouseover", function(d, i) {
                    // transition启动过渡，过渡持续的时间为duration毫秒
                    // mouseover到第i个layer上了，opacity再针对j进行判断，如果相等，那么opacity=1
                    svg.selectAll(".layer").transition()
                    .duration(mouseover_duration)
                    .attr("opacity", function(d, j) {   return j != i ? 0.6 : 1;    })
                })
            .on("mousemove", function(d, i) {
                mousex = d3.mouse(this);
                mousex = mousex[0];
                var invertedx = x.invert(mousex);
                invertedx = invertedx.getMonth() * 100 + invertedx.getDate();
                var selected = (d.values);
                for (var k = 0; k < selected.length; k++) {
                    datearray[k] = selected[k].date
                    datearray[k] = datearray[k].getMonth() * 100 + datearray[k].getDate();
                }
    
                mousedate = datearray.indexOf(invertedx);
                pro = parseInt(d.values[mousedate].value);
    
                d3.select(this)
                    // select(this)选中当前事件所在的那个元素
                    // classed用来选定或者删除某一个css的class，true的话就相当于添加一个class=hover
                    .classed("hover", true)
                    .attr("stroke", strokecolor)    // stroke width指的是包围在一个stream周围的，有一圈加粗的
                    .attr("stroke-width", "0.5px"), 
                    tooltip.html( "<p>" + d.key + "<br>" + pro + "</p>" ).style("visibility", "visible");
                })
            .on("mouseout", function(d, i) {
                svg.selectAll(".layer")
                    .transition()
                    .duration(mouseover_duration)
                    .attr("opacity", "1");
                d3.select(this)
                    .classed("hover", false)
                    .attr("stroke-width", "0px"), 
                    tooltip.html( "<p>" + d.key + "<br>" + pro + "</p>" )
                        .style("visibility", "hidden");
                })
            .on("dblclick", function(d, i){
                // 目前是展示所有数据，即将展示一部分数据                
                if(is_all == 1){
                    clear();
                    stream_filter(d.key);
                    which_one = d.key;
                    is_all = 0;
                }
                // 目前是展示部分数据，即将展示全部数据
                else if(is_all == 0){
                    if(which_one != d.key)
                        return;
                    
                    clear();
                    stream_filter("");
                    is_all = 1;
                }
            });
        // 那一条竖线
        var vertical = d3.select(".chart")
            .append("div")
            .attr("class", "remove")
            .style("position", "absolute")
            .style("z-index", "19")
            .style("width", "1px")
            .style("height", "380px")
            .style("top", "10px")
            .style("bottom", "30px")
            .style("left", "0px")
            .style("background", "#fff");
    
        d3.select(".chart")
            .on("mousemove", function(){  
                mousex = d3.mouse(this);
                mousex = mousex[0] + 5;
                vertical.style("left", mousex + "px" )
                })
            .on("mouseover", function(){  
                mousex = d3.mouse(this);
                mousex = mousex[0] + 5;
                vertical.style("left", mousex + "px")
                });
    }
    
    // d3.csv作用是读取全部的表格数据，然后转换成一个array，每一行一个元素
    // 每个元素通过一个object的方式进行呈现，最终读取到的结果就是下面的data
    function stream_filter(key){
        if(key == ""){
            d3.csv(csvpath, function(data) {
                allstream_preprocess(data, true);
                // update y function here
                y = d3.scale.linear().range([height - blank_total, 0]);
                paint(data);
            });
        }
        else{
            d3.csv(csvpath, function(data) {
                alldata = [];
                data.forEach(function(d){
                    if(d.key == which_one){
                        alldata.push(d);
                    }
                });
                local_maxval = 0;
                alldata.forEach(function(d) {
                    d.value = +d.value;
                    if(d.value > local_maxval){
                        local_maxval = d.value;
                    }
                });
                // update y function here
                var max_height = (height - blank_total) * local_maxval / global_maxval;
                y = d3.scale.linear().range([height - blank_total, height - blank_total - max_height]);
                paint(alldata);
            });
        }
    }
    
    // 最开始调用chart_allstream，默认显示allstream
    stream_filter("");
}

function chart_splitstream(csvpath) {
    // 全局的最大值
    var global_maxval = 0;

    // single_height = single_height_sum / num_of_stream
    var num_of_stream = 0;
    var single_height = 0;
    
    // 创建一块svg画布，设定高度，设定宽度
    // 在这一块svg上绘制所有的stream分量
    var svg = d3.select(".chart").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", single_height_sum + margin.top + margin.bottom)
        // g是group的意思，可以将元素进行分组，之后可能比较好管理吧，暂时没看到用处
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var datearray = [];

    function paint_split_single(index, key, data, local_maxval) {
        //console.log(local_maxval);
        //console.log(global_maxval);
        // d3.scale是创建比例尺，相当于是一个映射关系
        // domain是定义域，range是值域，默认为[0,1]
        // y相当于就是一个函数了，之后调用y(100.0)，返回映射后的值

        var max_height = (single_height - blank_single) * local_maxval / global_maxval;
        var start_ypos = (index + 1) * single_height;
        var end_ypos = start_ypos - max_height;
        var y = d3.scale.linear().range([start_ypos, end_ypos]);
        
        // 对于每一个data的object进行如下的处理，时间的格式化
        data.forEach(function(d) {
            d.date = format.parse(d.date);
            d.value = +d.value;
        });

        // 按照定义好的nest，将原始的一维data转换为二维data，然后传递给stack
        // 主要就是增加了y和y0，data原始数据中也添加了y0和y这些信息
        // 之后返回的layers是一个分层结构，但是data仍然是一维结构，只是增加了更多的内容，比如y0
        var layers = stack(nest.entries(data));
        // initialize color using linear interpolate
        color_linear.domain([0, layers.length]);
        strokecolor = compute(color_linear(0));

        x.domain(d3.extent(data, function(d) { return d.date; }));
        y.domain([0, d3.max(data, function(d) { return d.y0 + d.y; })]);
        // selectAll选中了一批元素，可能比需要的多，可能比需要的少，甚至可能为0个
        // data是数据，相当于一个array
        // enter函数，返回了数据比元素多的部分。update是数据和元素相同多的部分。exit是数据比元素少的部分

        // 好像是某种圆形插值的算法，给定一个数组，就能生成各种形状
        var area = d3.svg.area()
            .interpolate("cardinal")
            .x(function(d) { return x(d.date); })
            .y0(function(d) { return y(d.y0); })
            .y1(function(d) { return y(d.y0 + d.y); });
            
        var layer_name = "layer" + index;
        var select_layer_name = ".layer" + index;

        svg.selectAll(select_layer_name)
            .data(layers)
            .enter().append("path")
            .attr("class", layer_name)
            .attr("d", function(d) { return area(d.values); })
            .style("fill", function(d, i) { return random_color(index); });

        // 绘制x轴
        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + (index + 1) * single_height + ")")
            .call(xAxis);

        // 绘制标签
        var label_name = "lable" + index;
        var tooltip = d3.select("body")
            .append("div")
            .attr("class", label_name)
            .style("position", "absolute")
            .style("z-index", "20")
            .style("top", (index + label_location) * single_height + "px")
            .style("left", "55px");
        tooltip.html( "<p>" + key + "<br> 0 </p>" ).style("visibility", "visible");

        // 画竖线
        var line_name = "line" + index;
        var vertical = d3.select("body")
            .append("div")
            .attr("class", line_name)
            .style("position", "absolute")
            .style("z-index", "19")
            .style("width", "1px")
            .style("height", single_height + "px")
            .style("top", margin.top + blank_single + single_height * index + "px")
            .style("left", "0px")
            .style("background", "#fff");

        // 交互
        svg.selectAll(select_layer_name)
            .attr("opacity", 1)
            // select得到的每一个选择集都可以通过on添加事件监听器
            // 最新一次发生的时间会被保存到d3.event中，可以直接console.log(d3.event)查看
            // function(d, i)仍然是d标识对应的layer，i标识下标
            .on("mousemove", function(d, i) {
                mousex = d3.mouse(this);
                mousex = mousex[0];
                var invertedx = x.invert(mousex);
                invertedx = invertedx.getMonth() * 100 + invertedx.getDate();
                var selected = (d.values);
                for (var k = 0; k < selected.length; k++) {
                    datearray[k] = selected[k].date
                    datearray[k] = datearray[k].getMonth() * 100 + datearray[k].getDate();
                }
    
                mousedate = datearray.indexOf(invertedx);
                pro = parseInt(d.values[mousedate].value);
    
                tooltip.html( "<p>" + d.key + "<br>" + pro + "</p>" );

                linepos = mousex + margin.left + 5;
                vertical.style("left", linepos + "px");
                })
            .on("mouseout", function(d, i) {
                tooltip.html( "<p>" + d.key + "<br> 0 </p>" );
                vertical.style("left", "0px");
            });
    }

    function paint_split(data) {
        data.forEach(function(d) {
            d.value = +d.value;
        })

        // split data by key
        var spl_data = Array();
        data.forEach(function(d) {
            if(!spl_data[d.key])
                spl_data[d.key] = [];
            spl_data[d.key].push(d);
        });

        // get max value by key
        var max_val = Array();
        for(var key in spl_data){
            maxv = spl_data[key][0].value;
            for(var i=1; i<spl_data[key].length; i++)
                if(spl_data[key][i].value > maxv)
                    maxv = spl_data[key][i].value;
            max_val[key] = maxv;
        }

        // get global max value
        for(var key in max_val){
            if(max_val[key] > global_maxval)
                global_maxval = max_val[key];
        }

        // get the key with order
        var ordered_key = Array();
        var prev = "";
        data.forEach(function(d) {
            if(d.key != prev)
                ordered_key.push(d.key);
            prev = d.key;
        });

        // get num of stream, calculate height of each stream
        num_of_stream = ordered_key.length;
        single_height = single_height_sum / num_of_stream;

        // paint each single stream
        for(var i=0; i<ordered_key.length; i++){
            var key = ordered_key[i];
            paint_split_single(i, key, spl_data[key], max_val[key]);
        }
    }

    d3.csv(csvpath, function(data) {
        paint_split(data);
    });

}
