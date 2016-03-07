var datearray = [];

function chart(csvpath) {

    // color linear interpolate
    var red_color = d3.rgb(255,0,0);    //红色
    var green_color = d3.rgb(0,255,0);    //绿色
    var compute = d3.interpolate(red_color, green_color);
    var color_linear = d3.scale.linear().range([0,1]);

    var format = d3.time.format("%m/%d/%y");

    var margin = {top: 20, right: 40, bottom: 30, left: 30};
    var width = document.body.clientWidth - margin.left - margin.right;
    var height = 400 - margin.top - margin.bottom;

    // D3通过select来选中html中的某一些元素
    // 可以进行append，在后面插入新的html标签，也可以用insert在固定的位置插入，也可以用remove删除
    // 之后可以进行style相关的操作，就相当于是为html的元素添加新style了
    // 以下的代码就可以生成 <div class="remove" style="position:absolute, ..."

    // select特定的元素，可以用#，表示对id进行选择
    // 也可以用.，表示对class进行选择

    // svg添加文字，可以用append("text").text("some string...")

    // tooltip就是左上角显示那个class1,class2的地方
    var tooltip = d3.select("body")
        .append("div")
        .attr("class", "remove")
        .style("position", "absolute")
        .style("z-index", "20")
        .style("visibility", "hidden")
        .style("top", "30px")
        .style("left", "55px");

    // 可以在这里先设定一个值域，之后再在后面设置定义域
    // time.scale用法和scale一样
    var x = d3.time.scale()
        .range([0, width]);

    // d3.scale是创建比例尺，相当于是一个映射关系
    // domain是定义域，range是值域，默认为【0,1】
    // y相当于就是一个函数了，之后调用y(100.0)，返回映射后的值
    var y = d3.scale.linear()
        .range([height-10, 0]);

    // ordinal是基于序数的映射，应用在类似enumerate这样的元素上，不能任意细分
    // ordinal如果没有domain的话好像就随便映射了
    //var z = d3.scale.ordinal()
    //    .range(colorrange);

    // 创建坐标轴
    var xAxis = d3.svg.axis()
        .scale(x)   // 坐标轴一定是和一个比例尺绑定在一起的
        .orient("bottom")   // 刻度显示在什么方向，这里是在下面
        .ticks(d3.time.weeks);  // tick表示显示出多少个刻度，这个意思应该是每周显示一个刻度

    // layout相当于是一种数据转换，将原始的数据，转换为适合可视化的数据
    // 之后用stack初始化一批数据stack(data)，得到的data就能够按照你定义的如下形式进行操作了
    
    // stack图相当于是处理一个二维数组，横轴方向有若干列，每一列有是由若干block堆叠而成的
    var stack = d3.layout.stack()
        .offset("silhouette")
        .values(function(d) { return d.values; })   // 这句相当于一个设定，之后当我访问values的时候，我访问的是data的values，相当于是数组的第一维
                                // d.values，因为之前通过nest进行了转换，第一个维度是key : values的映射，所以values之后就指向数组的第二维了
        .x(function(d) { return d.date; })          // 当我访问x的时候，我访问的是data的date，这个是相对于values来说的，相当于是数组的第二维
        .y(function(d) { return d.value; });        // y相当于是每一个小block的高度，stack的layout会自动把所有的y叠加起来得到整体的高度的

    // nest将数据转换为层级标识，应该是类似高维数组，有点类似与SQL中的group by
    // 输入可能是一个一维数组，每个元素都是某种object，现在想要根据object中的某些属性，将数据转换成为高维数组
    // 每一层数据都自动转换成为key : values的形式
    var nest = d3.nest()
        .key(function(d) { return d.key; });        // d.key是data.csv中的key，也就是课程ID，用这个作为第一层的group by
        // 之后就得到数组的第一个维度了，相同课程ID的那些entry形成第二个维度
        // key函数可以连续调用，就可以生成更高维度的数组了

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

    // d3.csv作用是读取全部的表格数据，然后转换成一个array，每一行一个元素
    // 每个元素通过一个object的方式进行呈现，最终读取到的结果就是下面的data
    var graph = d3.csv(csvpath, function(data) {
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
        svg.selectAll(".layer")
            .data(layers)
            .enter().append("path")
            .attr("class", "layer")
            .attr("d", function(d) { return area(d.values); })
            .style("fill", function(d, i) { return compute(color_linear(i)); });

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
                    .duration(250)
                    .attr("opacity", function(d, j) {   return j != i ? 0.6 : 1;    })
                })
            .on("mousemove", function(d, i) {
                mousex = d3.mouse(this);
                mousex = mousex[0];
                var invertedx = x.invert(mousex);
                invertedx = invertedx.getMonth() + invertedx.getDate();
                var selected = (d.values);
                for (var k = 0; k < selected.length; k++) {
                    datearray[k] = selected[k].date
                    datearray[k] = datearray[k].getMonth() + datearray[k].getDate();
                }
    
                mousedate = datearray.indexOf(invertedx);
                pro = d.values[mousedate].value;
    
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
                    .duration(250)
                    .attr("opacity", "1");
                d3.select(this)
                    .classed("hover", false)
                    .attr("stroke-width", "0px"), tooltip.html( "<p>" + d.key + "<br>" + pro + "</p>" ).style("visibility", "hidden");
                })
        
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
    }); // endof graph = d3.csv...

}// endof function chart
