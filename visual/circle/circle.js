
function circle(treepath){
    var width = 450,
    height = 450,
    radius =  Math.min(width, height) / 2 ,
    color = d3.scale.category20();  // 自动生成20中颜色的预设，似乎可以把一个字符串映射成某一种颜色

    // 创建了一块画布，把画布的中心移动到了radius的位置
    var svg = d3.select("body").append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", "translate(" + (radius) + "," + (radius) + ")");

    // layout.partition()生成分区图
    // 可以类似树形结构那样横向地分割，也可以做成圆形的分割
    var partition = d3.layout.partition()
        .sort(null)     // sort标识节点是否进行排序，null就是不排序
        .size([2 * Math.PI, radius * radius])   // 绘图的范围，一般是[width, height]
            // 但是这里表示成了圆形的，圆形打开相当于是一个2pai的弧度，似乎圆形分区都是这样
        .value(function(d) { return d.value; });      
            // 节点大小是多少，在json文件中对对象扩展value即可
            // 实际上只需要最叶子节点的value就够了，父节点的value会自动一步步推算上去，不写或者写错了也没事

    // 绘制弧形的相关函数
    var arc = d3.svg.arc()
        .startAngle(function(d) { return d.x; })    // d指的就是经过partition处理之后的每一个data
            // 原先是x，y上的关系，现在x转变为一个angle，y转变为半径的差值
            // 就把原先横平竖直的一个方形转换成一个圆弧了
        .endAngle(function(d) { return d.x + d.dx; })
        .innerRadius(function(d) { return Math.sqrt(d.y); })
        .outerRadius(function(d) { return Math.sqrt(d.y + d.dy); });

    d3.json("city_tree.json", function(error, root) {
        if(error)
            console.log(error);
    
        // root数据的结构是一个name -> children的字典结构
        // 虽然最后没有用到links，但是links这一步转换是必不可少的，应该是在nodes里面添加了一些别的数据
        // 增加了有d.depth（是在哪一层）d.x, x.y（坐标起点）d.dx, d.dy（两个方向上的长度）
        // 还有d.children（指向儿子节点的指针），d.parent（指向父节点的指针）
        // 最外层节点没有children，最内层节点没有parent
        var nodes = partition.nodes(root);
        var links = partition.links(nodes);
    
        // nodes是一批零散的节点，并不包含partition的结构信息，而且已经包含了dx，dy之类的数据了
        //console.log(nodes);
    
        // 指向每一个弧形的时候开始更新，生成当前区域中最活跃的人
        var TopStudents = svg.append("text")
            .attr("font-size",20)
            .attr("font-family","simsun")
            .attr("x", "0")
            //.attr("transform", "translate(" + (radius) + "," + (radius) + ")")
        
        // 初始化最活跃学生群体        
        TopStudents.selectAll("tspan")
            .data(nodes[0].top)
            .enter()
            .append("tspan")
            .attr("dy", "1em")
            .attr("x", TopStudents.attr("x"))
            .text(function(d){
                return d;
            });
    
        var arcs = svg.selectAll("g")
            .data(nodes)
            .enter().append("g");
    
        arcs.append("path")
            // 最里层的那个是隐藏的，空白了
            .attr("display", function(d) { return d.depth ? null : "none"; }) // hide inner ring
            .attr("d", arc)     // 用之前定义的那个arc来画圆弧
            .style("stroke", "#fff")
            // 颜色，如果是最外层，就和里面一层的颜色一样
            .style("fill", function(d) { return color((d.children ? d : d.parent).name); })
            .on("mouseover",function(d, i){
                d3.select(this)
                    .style("fill","yellow");
                // 每次移动的时候，更新最活跃学生群体
                TopStudents.selectAll("tspan")
                    .data(nodes[i].top)
                    .attr("dy","1em")
                    .attr("x", TopStudents.attr("x"))
                    .text(function(d){
                        return d;
                    });
            })
            .on("mouseout",function(d){
                d3.select(this)
                    .transition()   // 过渡渐变效果
                    .duration(200)      // 经过200毫秒的渐变，变成下面的fill状态
                    .style("fill", function(d) { 
                        return color((d.children ? d : d.parent).name); 
                    });
            });
                      
        arcs.append("text")  
            .style("font-size", "12px")
            .style("font-family", "simsun")
            .attr("text-anchor","middle")
            .attr("transform",function(d,i){
                //其他的元素，既平移也旋转
                var r = 0;
                if( (d.x+d.dx/2)/Math.PI*180 < 180 )  // 0 - 180 度以内的
                    r = 180 * ((d.x + d.dx / 2 - Math.PI / 2) / Math.PI);
                else  // 180 - 360 度以内的
                    r = 180 * ((d.x + d.dx / 2 + Math.PI / 2) / Math.PI);
                        
                //既平移也旋转
                return  "translate(" + arc.centroid(d) + ")" +
                    "rotate(" + r + ")";
            }) 
            .text(function(d, i) { 
                if(i == 0)
                    return "";
                else 
                    return d.name;
            });
    });

}
