## Copyright (C) 2012 Bitergia
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## This file is a part of the vizgrimoire R package
##
## Authors:
##   Jesus M. Gonzalez-Barahona <jgb@bitergia.com>
##
##
## MultiAges class
##
## Class for handling ages of persons (for several points in time)
##
## This class is a child of Ages class
##
## Components of the class, same as Ages, with changes
##  - date: last point in time (as string, eg "2011-01-31"
##  - persons (dataframe): new variables
##     - date: point in time for the data in that record (observation)
##

setClass(Class="AgesMulti",
         contains="Ages"
         )

## Initialize by running the query that gets dates for population,
## and by initializing the data frames with specialized data
##
setMethod(f="initialize",
          signature="AgesMulti",
          definition=function(.Object,
                              ages.list){
            cat("~~~ AgesMulti: initializator ~~~ \n")
            date <- ""
            for (ages in ages.list) {
              if (ages@date > date) {
                date <- ages@date
              }
              ages@persons['date'] <- ages@date
              .Object@persons <- rbind (.Object@persons, ages@persons)
            }
            .Object@date <- date
            return(.Object)
          }
          )

##
## Create a JSON file out of an object of this class
##
## Parameters:
##  - filename: name of the JSON file to write
##
setMethod(
  f="JSON",
  signature="Ages",
  definition=function(.Object, filename) {
    sink(filename)
    cat(toJSON(list(date = .Object@date,
                    persons = as.data.frame(.Object@persons))))
    sink()
  }
  )

##
## Generic PyramidBar function
##
setGeneric (
  name= "PyramidBar",
  def=function(.Object,...){standardGeneric("PyramidBar")}
  )
##
## Plot bar pyramid of persons for a certain date
##
## The pyramid is built based on how long have they have stayed
## in the project the developers active at that date
##
## - filename: file to write pyramid to
## - periods: periods per year (1: year, 4: quarters, 12: months)
## - position: position of the bars for the same period
##    (usually one of "dodge", "identity", "stacked"
setMethod(
  f="PyramidBar",
  signature="AgesMulti",
  definition=function(.Object, filename = NULL, position = "dodge",
                      periods = 4) {
    if ((position == "dodge") | (position == "stacked")) {
      colors <- brewer.pal(8,"Dark2")
    } else {
      colors <- rev(brewer.pal(8,"Oranges"))
    }
    # Next is to capture "periods" in .e, needed for the ggplot call below
    .e <- environment()
    chart <- ggplot(data=.Object@persons, aes(x=floor(age/(365/periods)),
                      fill=date),
                    environment = .e) +
      geom_histogram(binwidth=1, position=position) +
      scale_fill_manual(values = colors) +
      xlab("Age") +
      ylab("Number of developers") +
      coord_flip()
    produce.charts (chart = chart, filename = filename,
                    height = 5, width = 4)
  }
  )    

##
## Generic PyramidFaceted function
##
setGeneric (
  name= "PyramidFaceted",
  def=function(.Object,...){standardGeneric("PyramidFaceted")}
  )
##
## Plot faceted bar pyramid of persons for a certain date
##
## The pyramid is built based on how long have they have stayed
## in the project the developers active at that date
##
## - filename: file to write pyramid to
## - periods: periods per year (1: year, 4: quarters, 12: months)
##
setMethod(
  f="PyramidFaceted",
  signature="AgesMulti",
  definition=function(.Object, filename = NULL, periods = 4,
                      fill="red") {
    # Next is to capture "periods" in .e, needed for the ggplot call below
    .e <- environment()
    chart <- ggplot(data=.Object@persons, aes(x=floor(age/(365/periods))),
                    environment = .e) +
      geom_histogram(binwidth=1, fill = fill, colour="black") +
      facet_wrap(~ date) +
      xlab("Age (quarters)") +
      ylab("Number of developers") +
      coord_flip()
    produce.charts (chart = chart, filename = filename,
                    height = 5, width = 4)
  }
  )    

##
## Generic Pyramid3D function
##
setGeneric (
  name= "Pyramid3D",
  def=function(.Object,...){standardGeneric("Pyramid3D")}
  )
##
## Plot 3D bar pyramid of persons for a certain date
##
## The pyramid is built based on how long have they have stayed
## in the project the developers active at that date
##
## - filename: file to write pyramid to
## - periods: periods per year (1: year, 4: quarters, 12: months)
##
setMethod(
  f="Pyramid3D",
  signature="AgesMulti",
  definition=function(.Object, dirname = NULL, periods = 4,
                      interactive = FALSE,
                      template = system.file(file.path("WebGL",
                                             "template.html"), 
                                             package = "rgl")) {
    rgl.open()
    rgl.bg(col="white")
    hist3d(x = .Object@persons$age, y = .Object@persons$date,
       x.nclass = floor(max(.Object@persons$age)/(365/periods)),
       y.nclass = "auto",
       y.scale = 200, z.scale = 5,
       cols = brewer.pal(8,"Dark2"),
       alpha = 0.7)
    if (!is.null(dirname)) {
      writeWebGL(dir = dirname, width=400, height=400, template = template)
    }
    if (interactive) {
      print ("Press RETURN to continue...")
      readline ()
    }
    rgl.close()
  }
  )    
